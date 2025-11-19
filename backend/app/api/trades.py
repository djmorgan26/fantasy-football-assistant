from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.database import get_database
from app.models.user import User
from app.models.league import League
from app.models.trade import Trade, TradeStatus
from app.schemas.trade import TradeAnalysisRequest, TradeAnalysisResponse, TradeCreate, TradeResponse
from app.core.auth import get_current_active_user
from app.services.espn_service import ESPNService, ESPNCookies, ESPNError
from app.services.llm_service import llm_service
from app.utils.encryption import ESPNCredentialManager
import structlog
from datetime import datetime, timedelta

logger = structlog.get_logger()
router = APIRouter(prefix="/trades", tags=["trades"])


@router.post("/analyze", response_model=TradeAnalysisResponse)
async def analyze_trade(
    trade_request: TradeAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        # Verify user has access to the league
        league_result = await db.execute(
            select(League).where(
                League.id == trade_request.league_id,
                League.owner_user_id == current_user.id
            )
        )
        league = league_result.scalar_one_or_none()
        
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="League not found"
            )
        
        espn_service = ESPNService()
        
        # Get ESPN credentials
        cookies = None
        if league.espn_s2_encrypted or league.espn_swid_encrypted:
            s2 = ESPNCredentialManager.decrypt_espn_s2(league.espn_s2_encrypted) if league.espn_s2_encrypted else None
            swid = ESPNCredentialManager.decrypt_espn_swid(league.espn_swid_encrypted) if league.espn_swid_encrypted else None
            if s2 or swid:
                cookies = ESPNCookies(espn_s2=s2, swid=swid)
        
        # Validate the trade with ESPN
        validation_result = await espn_service.validate_trade(
            str(league.espn_league_id),
            trade_request.proposing_team_id,
            trade_request.receiving_team_id,
            trade_request.give_players,
            trade_request.receive_players,
            cookies
        )
        
        if not validation_result.get("is_valid", False):
            return TradeAnalysisResponse(
                is_valid=False,
                analysis_summary=validation_result.get("error", "Trade validation failed"),
                recommendations=["Please check that all players are on the correct rosters"]
            )
        
        # Get player details for analysis
        # This is a simplified analysis - in a full implementation you'd want
        # more sophisticated player valuation and team need analysis
        
        try:
            proposing_roster = await espn_service.get_team_roster(
                str(league.espn_league_id),
                trade_request.proposing_team_id,
                cookies=cookies
            )
            receiving_roster = await espn_service.get_team_roster(
                str(league.espn_league_id),
                trade_request.receiving_team_id,
                cookies=cookies
            )
            
            # Simple analysis based on projected points
            give_total_points = 0
            receive_total_points = 0
            give_player_details = {}
            receive_player_details = {}
            
            # Calculate totals for players being given away
            for player in proposing_roster["roster"]:
                if player["player_id"] in trade_request.give_players:
                    projected = player.get("stats", {}).get("projected", {}).get("0", 0)
                    give_total_points += projected
                    give_player_details[player["player_id"]] = {
                        "name": player["full_name"],
                        "position": player["position_name"],
                        "projected_points": projected
                    }
            
            # Calculate totals for players being received
            for player in receiving_roster["roster"]:
                if player["player_id"] in trade_request.receive_players:
                    projected = player.get("stats", {}).get("projected", {}).get("0", 0)
                    receive_total_points += projected
                    receive_player_details[player["player_id"]] = {
                        "name": player["full_name"],
                        "position": player["position_name"],
                        "projected_points": projected
                    }
            
            value_difference = receive_total_points - give_total_points

            # Calculate fairness score (0-100)
            if give_total_points == 0 and receive_total_points == 0:
                fairness_score = 50.0
            elif give_total_points == 0:
                fairness_score = 0.0
            else:
                ratio = receive_total_points / give_total_points
                # Score closer to 100 when ratio is closer to 1.0
                fairness_score = max(0, 100 - abs(ratio - 1.0) * 100)

            # Use LLM for enhanced analysis if available
            recommendations = []
            analysis_summary = ""

            if llm_service.is_available():
                try:
                    # Prepare player data for LLM
                    give_players_data = [give_player_details[pid] for pid in trade_request.give_players if pid in give_player_details]
                    receive_players_data = [receive_player_details[pid] for pid in trade_request.receive_players if pid in receive_player_details]

                    # Get LLM analysis
                    llm_analysis = await llm_service.analyze_trade(
                        give_players=give_players_data,
                        receive_players=receive_players_data,
                        user_roster=proposing_roster["roster"][:15],
                        opponent_roster=receiving_roster["roster"][:15],
                        league_settings={"scoring_type": "standard"}
                    )

                    # Use LLM results
                    fairness_score = llm_analysis.get("fairness_score", fairness_score)
                    value_difference = llm_analysis.get("value_difference", value_difference)
                    analysis_summary = llm_analysis.get("analysis_summary", "")
                    recommendations = llm_analysis.get("recommendations", [])

                    # Add LLM insights to player details
                    if "pros" in llm_analysis and llm_analysis["pros"]:
                        recommendations.insert(0, f"Pros: {', '.join(llm_analysis['pros'][:2])}")
                    if "cons" in llm_analysis and llm_analysis["cons"]:
                        recommendations.append(f"Cons: {', '.join(llm_analysis['cons'][:2])}")

                except Exception as llm_error:
                    logger.warning("LLM trade analysis failed, using basic analysis", error=str(llm_error))

            # Fallback to basic analysis if LLM not available or failed
            if not analysis_summary:
                if value_difference > 5:
                    recommendations.append("This trade favors you significantly - great deal!")
                elif value_difference > 2:
                    recommendations.append("This trade slightly favors you")
                elif value_difference > -2:
                    recommendations.append("This is a fairly balanced trade")
                elif value_difference > -5:
                    recommendations.append("This trade slightly favors your opponent")
                else:
                    recommendations.append("This trade heavily favors your opponent - consider carefully")

                if fairness_score < 60:
                    recommendations.append("Consider looking for more balanced alternatives")

                analysis_summary = f"Trade analysis: You give {len(trade_request.give_players)} player(s) for {len(trade_request.receive_players)} player(s). "
                analysis_summary += f"Projected point difference: {value_difference:+.1f}. "
                analysis_summary += f"Fairness score: {fairness_score:.0f}/100."
            
            return TradeAnalysisResponse(
                is_valid=True,
                fairness_score=fairness_score,
                value_difference=value_difference,
                analysis_summary=analysis_summary,
                recommendations=recommendations,
                player_details={
                    "give": give_player_details,
                    "receive": receive_player_details
                }
            )
            
        except Exception as roster_error:
            logger.warning("Could not get detailed roster analysis", error=str(roster_error))
            return TradeAnalysisResponse(
                is_valid=True,
                analysis_summary="Trade appears valid but detailed analysis unavailable",
                recommendations=["Manual evaluation recommended"]
            )
        
    except HTTPException:
        raise
    except ESPNError as e:
        logger.error("ESPN API error analyzing trade", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not validate trade with ESPN: {str(e)}. Please verify your league credentials and player IDs."
        )
    except ValueError as e:
        logger.warning("Invalid trade data", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid trade: {str(e)}"
        )
    except Exception as e:
        logger.error("Failed to analyze trade", error=str(e), exc_info=True)
        error_detail = "Failed to analyze trade. "
        if "player" in str(e).lower():
            error_detail += "One or more players may not be on the expected rosters."
        elif "timeout" in str(e).lower():
            error_detail += "ESPN API timed out. Please try again."
        else:
            error_detail += "Please verify your trade details and try again."
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.post("/", response_model=TradeResponse)
async def create_trade(
    trade_data: TradeCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        # Verify user has access to the league
        league_result = await db.execute(
            select(League).where(
                League.id == trade_data.league_id,
                League.owner_user_id == current_user.id
            )
        )
        league = league_result.scalar_one_or_none()
        
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="League not found"
            )
        
        # Create trade record
        trade = Trade(
            league_id=trade_data.league_id,
            proposing_team_id=trade_data.proposing_team_id,
            receiving_team_id=trade_data.receiving_team_id,
            user_id=current_user.id,
            proposed_players={
                "give": trade_data.give_players,
                "receive": trade_data.receive_players
            },
            status=TradeStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(days=7)  # Expire in 7 days
        )
        
        db.add(trade)
        await db.commit()
        await db.refresh(trade)
        
        return TradeResponse.from_orm(trade)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create trade", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create trade"
        )


@router.get("/", response_model=List[TradeResponse])
async def get_user_trades(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        result = await db.execute(
            select(Trade).where(Trade.user_id == current_user.id)
            .order_by(Trade.created_at.desc())
        )
        trades = result.scalars().all()
        
        return [TradeResponse.from_orm(trade) for trade in trades]
        
    except Exception as e:
        logger.error("Failed to get user trades", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve trades"
        )


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        result = await db.execute(
            select(Trade).where(
                Trade.id == trade_id,
                Trade.user_id == current_user.id
            )
        )
        trade = result.scalar_one_or_none()
        
        if not trade:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trade not found"
            )
        
        return TradeResponse.from_orm(trade)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get trade", trade_id=trade_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve trade"
        )
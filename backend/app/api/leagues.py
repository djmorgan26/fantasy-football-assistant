from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from sqlalchemy.sql import func
from typing import List, Optional
from datetime import datetime, timezone
from app.db.database import get_database
from app.models.user import User
from app.models.league import League, PlatformType
from app.models.league_member import LeagueMember
from app.models.team import Team
from app.models.matchup import Matchup
from app.models.waiver_budget import WaiverBudget, WaiverTransaction
from app.services.sleeper_service import SleeperError
from app.schemas.league import (
    LeagueConnectionRequest, 
    LeagueConnectionResponse, 
    LeagueResponse
)
from app.schemas.matchup import MatchupResponse, MatchupWithTeams
from app.schemas.waiver_budget import (
    WaiverBudgetResponse, 
    TeamBudgetSummary,
    WaiverTransactionResponse
)
from app.core.auth import get_current_active_user
from app.services.espn_service import ESPNService, ESPNCookies, ESPNError
from app.utils.encryption import ESPNCredentialManager
from app.services.league_access import ensure_member, visible_to
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/leagues", tags=["leagues"])


@router.post("/connect", response_model=LeagueConnectionResponse)
async def connect_league(
    connection_request: LeagueConnectionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        espn_service = ESPNService()
        
        # Create ESPN cookies object
        cookies = None
        if connection_request.espn_s2 or connection_request.espn_swid:
            cookies = ESPNCookies(
                espn_s2=connection_request.espn_s2,
                swid=connection_request.espn_swid
            )
        elif current_user.espn_s2_encrypted or current_user.espn_swid_encrypted:
            # Use user's stored credentials
            user_cookies = ESPNCredentialManager.get_espn_cookies_for_user(current_user)
            if user_cookies:
                cookies = ESPNCookies(
                    espn_s2=user_cookies.get("espn_s2"),
                    swid=user_cookies.get("SWID")
                )
        
        # Test connection and get league info
        league_info = await espn_service.get_league_info(
            str(connection_request.league_id),
            cookies
        )
        
        # Get team data
        teams_data = await espn_service.get_teams(
            str(connection_request.league_id),
            cookies
        )
        
        # Check if league already exists
        result = await db.execute(
            select(League).where(League.espn_league_id == connection_request.league_id)
        )
        existing_league = result.scalar_one_or_none()
        
        if existing_league:
            # Update existing league
            league = existing_league
            league.name = league_info["name"]
            league.season_year = league_info["season"]
            league.size = league_info["size"]
            league.current_week = league_info["current_week"]
            league.scoring_type = league_info["scoring_type"]
            league.roster_settings = league_info["roster_settings"]
            league.scoring_settings = league_info["scoring_settings"]
            # Do NOT reassign ownership. A league row is shared by the managers
            # in it, and overwriting the owner here is how the second person to
            # connect an ESPN league used to lock the first one out of it.
            if league.owner_user_id is None:
                league.owner_user_id = current_user.id
            league.is_active = True  # Always set to active when connecting
        else:
            # Create new league
            league = League(
                espn_league_id=connection_request.league_id,
                name=league_info["name"],
                season_year=league_info["season"],
                size=league_info["size"],
                current_week=league_info["current_week"],
                scoring_type=league_info["scoring_type"],
                roster_settings=league_info["roster_settings"],
                scoring_settings=league_info["scoring_settings"],
                owner_user_id=current_user.id,
                is_active=True  # Always set to active when connecting
            )
            db.add(league)
        
        # Store encrypted credentials if provided
        if connection_request.espn_s2:
            league.espn_s2_encrypted = ESPNCredentialManager.encrypt_espn_s2(
                connection_request.espn_s2
            )
        if connection_request.espn_swid:
            league.espn_swid_encrypted = ESPNCredentialManager.encrypt_espn_swid(
                connection_request.espn_swid
            )
        
        await db.commit()
        await db.refresh(league)

        # Whoever connected it belongs in it, first manager or fifth.
        await ensure_member(
            db,
            league.id,
            current_user.id,
            role="owner" if league.owner_user_id == current_user.id else "member",
        )
        await db.commit()

        # Create/update teams
        for team_data in teams_data:
            result = await db.execute(
                select(Team).where(
                    Team.league_id == league.id,
                    Team.espn_team_id == team_data["id"]
                )
            )
            existing_team = result.scalar_one_or_none()
            
            if existing_team:
                # Update existing team
                team = existing_team
                team.name = team_data["name"]
                team.location = team_data["location"]
                team.nickname = team_data["nickname"]
                team.abbreviation = team_data["abbreviation"]
                team.logo_url = team_data["logo_url"]
                team.wins = team_data["wins"]
                team.losses = team_data["losses"]
                team.ties = team_data["ties"]
                team.points_for = team_data["points_for"]
                team.points_against = team_data["points_against"]
            else:
                # Create new team
                team = Team(
                    espn_team_id=team_data["id"],
                    league_id=league.id,
                    name=team_data["name"],
                    location=team_data["location"],
                    nickname=team_data["nickname"],
                    abbreviation=team_data["abbreviation"],
                    logo_url=team_data["logo_url"],
                    wins=team_data["wins"],
                    losses=team_data["losses"],
                    ties=team_data["ties"],
                    points_for=team_data["points_for"],
                    points_against=team_data["points_against"]
                )
                db.add(team)
        
        await db.commit()
        
        return LeagueConnectionResponse(
            success=True,
            message="League connected successfully",
            league=LeagueResponse.from_orm(league),
            teams=teams_data
        )
        
    except ESPNError as e:
        logger.error("ESPN API error during league connection", error=str(e))
        return LeagueConnectionResponse(
            success=False,
            message=f"ESPN connection failed: {str(e)}"
        )
    except Exception as e:
        logger.error("Unexpected error during league connection", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect to league"
        )


@router.get("/", response_model=List[LeagueResponse])
async def get_user_leagues(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        result = await db.execute(
            select(League).where(
                visible_to(current_user.id),
                League.is_active == True
            )
        )
        leagues = result.scalars().all()
        return [LeagueResponse.from_orm(league) for league in leagues]
    except Exception as e:
        logger.error("Failed to get user leagues", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve leagues"
        )


@router.get("/{league_id}", response_model=LeagueResponse)
async def get_league(
    league_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        result = await db.execute(
            select(League).where(
                League.id == league_id,
                visible_to(current_user.id)
            )
        )
        league = result.scalar_one_or_none()
        
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="League not found"
            )
        
        return LeagueResponse.from_orm(league)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get league", league_id=league_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve league"
        )


@router.post("/{league_id}/sync", response_model=LeagueConnectionResponse)
async def sync_league(
    league_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        # Get the existing league
        result = await db.execute(
            select(League).where(
                League.id == league_id,
                visible_to(current_user.id)
            )
        )
        league = result.scalar_one_or_none()
        
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="League not found"
            )
        
        # Sleeper leagues refresh through their own path; before this they
        # could not be re-synced at all, so records and the current week stayed
        # frozen at whatever they were when the league was connected.
        if league.platform == PlatformType.SLEEPER:
            from app.services.sleeper_sync import refresh_league

            teams_synced, week = await refresh_league(league, db)
            league.last_synced = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(league)
            return LeagueConnectionResponse(
                success=True,
                message=f"Synced {teams_synced} teams (week {week})",
                league=LeagueResponse.from_orm(league),
            )

        if league.platform == PlatformType.YAHOO:
            from app.services.yahoo_service import YahooError, YahooService

            try:
                data, teams_data = await YahooService().league_and_teams(current_user, league.yahoo_league_key)
            except YahooError as exc:
                return LeagueConnectionResponse(success=False, message=f"Yahoo sync failed: {exc}")

            league.name = data.get("name") or league.name
            league.season_year = int(data.get("season") or league.season_year)
            league.size = int(data.get("num_teams") or len(teams_data) or league.size)
            league.last_synced = datetime.now(timezone.utc)
            existing = {
                team.yahoo_team_key: team
                for team in (await db.execute(select(Team).where(Team.league_id == league.id))).scalars().all()
            }
            for team_data in teams_data:
                team = existing.get(team_data["id"])
                if team is None:
                    team = Team(league_id=league.id, yahoo_team_key=team_data["id"], name=team_data["name"])
                    db.add(team)
                team.name, team.abbreviation, team.logo_url = team_data["name"], team_data["abbreviation"], team_data["logo_url"]
                team.wins, team.losses, team.ties = team_data["wins"], team_data["losses"], team_data["ties"]
                team.points_for, team.points_against = team_data["points_for"], team_data["points_against"]
            await db.commit()
            await db.refresh(league)
            return LeagueConnectionResponse(
                success=True, message=f"Synced {len(teams_data)} Yahoo teams", league=LeagueResponse.from_orm(league), teams=teams_data,
            )

        espn_service = ESPNService()
        
        # Get stored credentials if available
        cookies = None
        if league.espn_s2_encrypted or league.espn_swid_encrypted:
            # Create temporary cookies object from league credentials
            cookies = ESPNCookies(
                espn_s2=ESPNCredentialManager.decrypt_espn_s2(league.espn_s2_encrypted) if league.espn_s2_encrypted else None,
                swid=ESPNCredentialManager.decrypt_espn_swid(league.espn_swid_encrypted) if league.espn_swid_encrypted else None
            )
        
        # Fetch fresh league data
        league_info = await espn_service.get_league_info(
            str(league.espn_league_id),
            cookies
        )
        
        # Update league with fresh data
        league.name = league_info["name"]
        # ESPN keeps the same league id across seasons, so a sync has to roll the
        # stored season forward or every downstream fetch stays on last year.
        league.season_year = league_info["season"]
        league.size = league_info["size"]
        league.current_week = league_info["current_week"]
        league.scoring_type = league_info["scoring_type"]
        league.roster_settings = league_info["roster_settings"]
        league.scoring_settings = league_info["scoring_settings"]
        league.last_synced = func.now()
        
        # Get fresh team data
        teams_data = await espn_service.get_teams(
            str(league.espn_league_id),
            cookies
        )
        
        # Update teams
        for team_data in teams_data:
            result = await db.execute(
                select(Team).where(
                    Team.league_id == league.id,
                    Team.espn_team_id == team_data["id"]
                )
            )
            existing_team = result.scalar_one_or_none()
            
            if existing_team:
                # Update existing team
                team = existing_team
                team.name = team_data["name"]
                team.location = team_data["location"]
                team.nickname = team_data["nickname"]
                team.abbreviation = team_data["abbreviation"]
                team.logo_url = team_data["logo_url"]
                team.wins = team_data["wins"]
                team.losses = team_data["losses"]
                team.ties = team_data["ties"]
                team.points_for = team_data["points_for"]
                team.points_against = team_data["points_against"]
            else:
                # Create new team
                team = Team(
                    espn_team_id=team_data["id"],
                    league_id=league.id,
                    name=team_data["name"],
                    location=team_data["location"],
                    nickname=team_data["nickname"],
                    abbreviation=team_data["abbreviation"],
                    logo_url=team_data["logo_url"],
                    wins=team_data["wins"],
                    losses=team_data["losses"],
                    ties=team_data["ties"],
                    points_for=team_data["points_for"],
                    points_against=team_data["points_against"]
                )
                db.add(team)
        
        await db.commit()
        await db.refresh(league)
        
        return LeagueConnectionResponse(
            success=True,
            message="League data synced successfully",
            league=LeagueResponse.from_orm(league),
            teams=teams_data
        )
        
    except ESPNError as e:
        logger.error("ESPN API error during league sync", error=str(e))
        return LeagueConnectionResponse(
            success=False,
            message=f"ESPN sync failed: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error during league sync", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync league data"
        )


@router.delete("/{league_id}")
async def disconnect_league(
    league_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        result = await db.execute(
            select(League).where(
                League.id == league_id,
                visible_to(current_user.id)
            )
        )
        league = result.scalar_one_or_none()
        
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="League not found"
            )
        
        # A league row is shared now, so "disconnect" means two different
        # things. The owner takes it down; anyone else just leaves, and
        # deactivating it for the whole league would be a surprise.
        if league.owner_user_id == current_user.id:
            league.is_active = False
        await db.execute(
            delete(LeagueMember).where(
                LeagueMember.league_id == league.id,
                LeagueMember.user_id == current_user.id,
            )
        )
        await db.commit()

        return {"message": "League disconnected successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to disconnect league", league_id=league_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect league"
        )


@router.get("/{league_id}/matchups-test")
async def test_matchups_simple(
    league_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    return {"message": "Test endpoint works", "league_id": league_id, "user_id": current_user.id}

@router.get("/{league_id}/matchups", response_model=List[MatchupWithTeams])
async def get_league_matchups(
    league_id: int,
    week: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        # Get the league and verify ownership
        result = await db.execute(
            select(League).where(
                League.id == league_id,
                visible_to(current_user.id)
            )
        )
        league = result.scalar_one_or_none()
        
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="League not found"
            )
        
        # Both platforms normalize to the same home/away shape; they differ in
        # how they express a pairing and in which column identifies a team.
        if league.platform == PlatformType.SLEEPER:
            from app.services.sleeper_sync import normalized_matchups

            matchups_data = await normalized_matchups(
                league.sleeper_league_id, week or league.current_week or 1
            )
            team_column = Team.sleeper_roster_id
        elif league.platform == PlatformType.YAHOO:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Yahoo matchup sync is not available yet.",
            )
        else:
            espn_service = ESPNService()
            cookies = None
            if league.espn_s2_encrypted or league.espn_swid_encrypted:
                cookies = ESPNCookies(
                    espn_s2=ESPNCredentialManager.decrypt_espn_s2(league.espn_s2_encrypted) if league.espn_s2_encrypted else None,
                    swid=ESPNCredentialManager.decrypt_espn_swid(league.espn_swid_encrypted) if league.espn_swid_encrypted else None
                )
            matchups_data = await espn_service.get_matchups(
                str(league.espn_league_id),
                week,
                cookies
            )
            team_column = Team.espn_team_id

        matchups_with_teams = []
        for matchup_data in matchups_data:
            # Get team details
            home_team = None
            away_team = None

            if matchup_data.get("home_team_id"):
                result = await db.execute(
                    select(Team).where(
                        Team.league_id == league.id,
                        team_column == matchup_data["home_team_id"]
                    )
                )
                home_team = result.scalar_one_or_none()

            if matchup_data.get("away_team_id"):
                result = await db.execute(
                    select(Team).where(
                        Team.league_id == league.id,
                        team_column == matchup_data["away_team_id"]
                    )
                )
                away_team = result.scalar_one_or_none()
            
            # Create response directly from ESPN data
            matchup_with_teams = MatchupWithTeams(
                id=matchup_data["matchup_id"],  # Use ESPN matchup ID as temporary ID
                matchup_id=matchup_data["matchup_id"],
                league_id=league.id,
                week=matchup_data["week"],
                home_team_id=home_team.id if home_team else None,
                away_team_id=away_team.id if away_team else None,
                home_score=matchup_data["home_score"],
                away_score=matchup_data["away_score"],
                home_projected_score=matchup_data.get("home_projected_score"),
                away_projected_score=matchup_data.get("away_projected_score"),
                is_playoff=matchup_data["is_playoff"],
                winner=matchup_data["winner"],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                home_team_name=home_team.name if home_team else None,
                away_team_name=away_team.name if away_team else None,
                home_team_location=home_team.location if home_team else None,
                away_team_location=away_team.location if away_team else None,
                home_team_nickname=home_team.nickname if home_team else None,
                away_team_nickname=away_team.nickname if away_team else None
            )
            matchups_with_teams.append(matchup_with_teams)
        
        return matchups_with_teams
        
    except ESPNError as e:
        logger.error("ESPN API error getting matchups", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ESPN API error: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error("Failed to get matchups", league_id=league_id, error=str(e), traceback=traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve matchups"
        )


@router.get("/{league_id}/waiver-budgets", response_model=List[TeamBudgetSummary])
async def get_league_waiver_budgets(
    league_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        # Get the league and verify ownership
        result = await db.execute(
            select(League).where(
                League.id == league_id,
                visible_to(current_user.id)
            )
        )
        league = result.scalar_one_or_none()
        
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="League not found"
            )
        
        # Both platforms report FAAB, in different places and shapes; each
        # service normalizes to {team_id, total_budget, spent_budget,
        # current_budget}, where team_id is that platform's own team key.
        if league.platform == PlatformType.SLEEPER:
            from app.services.sleeper_service import get_waiver_budgets as sleeper_budgets

            budgets_data = await sleeper_budgets(league.sleeper_league_id)
            team_column = Team.sleeper_roster_id
        elif league.platform == PlatformType.YAHOO:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Yahoo waiver-budget sync is not available yet.",
            )
        else:
            espn_service = ESPNService()
            cookies = None
            if league.espn_s2_encrypted or league.espn_swid_encrypted:
                cookies = ESPNCookies(
                    espn_s2=ESPNCredentialManager.decrypt_espn_s2(league.espn_s2_encrypted) if league.espn_s2_encrypted else None,
                    swid=ESPNCredentialManager.decrypt_espn_swid(league.espn_swid_encrypted) if league.espn_swid_encrypted else None
                )
            budgets_data = await espn_service.get_waiver_budgets(
                str(league.espn_league_id),
                cookies
            )
            team_column = Team.espn_team_id

        # Update budget data in database and prepare response
        budget_summaries = []
        for budget_data in budgets_data:
            # Find the corresponding team
            result = await db.execute(
                select(Team).where(
                    Team.league_id == league.id,
                    team_column == budget_data["team_id"]
                )
            )
            team = result.scalar_one_or_none()
            
            if not team:
                continue
                
            # Check if waiver budget record exists
            result = await db.execute(
                select(WaiverBudget).where(
                    WaiverBudget.team_id == team.id,
                    WaiverBudget.league_id == league.id,
                    WaiverBudget.season_year == league.season_year
                )
            )
            budget_record = result.scalar_one_or_none()
            
            if budget_record:
                # Update existing record
                budget_record.total_budget = budget_data["total_budget"]
                budget_record.current_budget = budget_data["current_budget"]
                budget_record.spent_budget = budget_data["spent_budget"]
            else:
                # Create new record
                budget_record = WaiverBudget(
                    league_id=league.id,
                    team_id=team.id,
                    total_budget=budget_data["total_budget"],
                    current_budget=budget_data["current_budget"],
                    spent_budget=budget_data["spent_budget"],
                    season_year=league.season_year
                )
                db.add(budget_record)
            
            # Sleeper hands back live bids with the budget; ESPN does not, so
            # its card falls back to whatever the transactions table has synced.
            live_transactions = budget_data.get("recent_transactions")
            if live_transactions:
                recent = [
                    WaiverTransactionResponse(
                        id=index,
                        league_id=league.id,
                        team_id=team.id,
                        player_id=tx.get("player_id") or 0,
                        player_name=tx.get("player_name") or "Waiver claim",
                        bid_amount=tx.get("bid_amount") or 0,
                        status=tx.get("status") or "SUCCESSFUL",
                        transaction_type=tx.get("transaction_type") or "ADD",
                        week=tx.get("week") or (league.current_week or 1),
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    for index, tx in enumerate(live_transactions, start=1)
                ]
            else:
                result = await db.execute(
                    select(WaiverTransaction).where(
                        WaiverTransaction.team_id == team.id,
                        WaiverTransaction.league_id == league.id
                    ).order_by(WaiverTransaction.created_at.desc()).limit(5)
                )
                recent = [WaiverTransactionResponse.from_orm(t) for t in result.scalars().all()]
            
            budget_summary = TeamBudgetSummary(
                team_id=team.id,
                team_name=team.name,
                current_budget=budget_data["current_budget"],
                spent_budget=budget_data["spent_budget"],
                total_budget=budget_data["total_budget"],
                recent_transactions=recent
            )
            budget_summaries.append(budget_summary)
        
        await db.commit()
        return budget_summaries
        
    except (ESPNError, SleeperError) as e:
        logger.error("Platform API error getting waiver budgets", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not reach the league platform: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get waiver budgets", league_id=league_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve waiver budgets"
        )

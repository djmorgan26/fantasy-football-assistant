import asyncio
from dataclasses import dataclass
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any, Dict, List, Optional
from app.db.database import get_database
from app.models.user import User
from app.models.league import League, PlatformType
from app.models.team import Team
from app.models.trade import Trade, TradeStatus
from app.schemas.trade import (
    CounterRequest,
    CounterResponse,
    PlayoffOdds,
    SleeperTokenRequest,
    TradeAnalysisRequest,
    TradeAnalysisResponse,
    TradeCreate,
    TradeEvaluation,
    TradeEvaluationRequest,
    TradeFinderResponse,
    TradeOffersResponse,
    TradeResponse,
)
from app.core.auth import get_current_active_user
from app.services.espn_service import ESPNService, ESPNCookies, ESPNError
from app.services.sleeper_service import SleeperAuthError
from app.services.llm_service import llm_service
from app.services import league_context, player_intel, trade_engine, trade_feed
from app.utils.encryption import ESPNCredentialManager, decrypt_data, encrypt_data
from app.services.league_access import visible_to
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
                visible_to(current_user.id)
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
                    projected = player.get("projected_points") or player.get("applied_points") or 0
                    give_total_points += projected
                    give_player_details[player["player_id"]] = {
                        "name": player["full_name"],
                        "position": player["position_name"],
                        "projected_points": projected
                    }
            
            # Calculate totals for players being received
            for player in receiving_roster["roster"]:
                if player["player_id"] in trade_request.receive_players:
                    projected = player.get("projected_points") or player.get("applied_points") or 0
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
                visible_to(current_user.id)
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

# ===========================================================================
# The trade workbench
#
# Everything below addresses teams and players by *our* ids, works for ESPN and
# Sleeper alike, and is what the rebuilt Trades page consumes. The /analyze
# endpoint above predates it: ESPN-only, player ids typed in by hand.
# ===========================================================================


@dataclass
class TradeContext:
    """Everything the trade endpoints need about a league, loaded once."""

    league: League
    teams: List[Team]
    my_team: Optional[Team]
    rosters: Dict[int, List[dict]]
    slots: trade_engine.LineupSlots
    levels: Dict[str, float]

    def team(self, team_id: int) -> Team:
        found = next((t for t in self.teams if t.id == team_id), None)
        if not found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team {team_id} is not in this league",
            )
        return found

    def roster(self, team_id: int) -> List[dict]:
        return self.rosters.get(team_id, [])

    @property
    def team_names(self) -> Dict[int, str]:
        return {t.id: t.name for t in self.teams}


async def _load_context(
    league_id: int, user: User, db: AsyncSession
) -> TradeContext:
    """Load the league, its teams and every roster, then derive the baselines.

    Rosters are fetched concurrently: a 12-team league is 12 platform calls and
    doing them in series is the difference between a page that feels instant and
    one that times out on a cold cache.

    Replacement levels are computed across *every rostered player in the
    league*, not just the two teams trading. That is the whole point of a
    replacement baseline: what a player is worth depends on what else exists.
    """
    league = await league_context.load_league(league_id, user, db)
    teams = await league_context.all_teams(league, db)
    if not teams:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This league has no synced teams yet. Sync the league and try again.",
        )
    mine = await league_context.my_team(league, user, db)

    loaded = await asyncio.gather(
        *(league_context.roster_for(league, t) for t in teams)
    )
    rosters = {team.id: entries for team, entries in zip(teams, loaded)}

    settings_blob = league.roster_settings or {}
    slots = trade_engine.lineup_slots_from_settings(
        settings_blob, settings_blob.get("roster_positions")
    )
    every_player = [p for entries in rosters.values() for p in entries]
    levels = trade_engine.replacement_levels(every_player, slots, len(teams))

    return TradeContext(
        league=league,
        teams=teams,
        my_team=mine,
        rosters=rosters,
        slots=slots,
        levels=levels,
    )


def _sleeper_token(league: League) -> Optional[str]:
    if not league.sleeper_token_encrypted:
        return None
    return decrypt_data(league.sleeper_token_encrypted)


def _playoff_spots(league: League) -> int:
    """How many teams make the playoffs, defaulting to the usual half-ish."""
    raw = (league.roster_settings or {}).get("playoff_teams")
    try:
        spots = int(raw)
    except (TypeError, ValueError):
        spots = 0
    if spots <= 0:
        spots = max(2, round((league.size or 10) / 2))
    return min(spots, max(1, (league.size or 10) - 1))


@router.get("/league/{league_id}/offers", response_model=TradeOffersResponse)
async def get_league_offers(
    league_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """Pending trade offers and recent trade history for a league.

    The headline feature: until now the app could not see that somebody had
    offered you a trade at all.
    """
    context = await _load_context(league_id, current_user, db)
    token = _sleeper_token(context.league)

    # Say plainly why pending offers might be missing, because on Sleeper it is
    # a thing the user can fix and on ESPN it is not.
    available, notice = True, None
    trades: List[trade_feed.NormalizedTrade] = []

    try:
        trades = await trade_feed.fetch_trades(
            context.league,
            context.teams,
            context.my_team,
            context.rosters,
            cookies=league_context.espn_cookies(context.league),
            sleeper_token=token,
        )
    except SleeperAuthError:
        # A stale token silently returning nothing rendered as "nobody has
        # offered you a trade", which is a different and wrong statement.
        logger.info("Stored Sleeper token rejected", league_id=league_id)
        available = False
        notice = (
            "Sleeper rejected your saved token, so pending offers cannot be "
            "read. Tokens expire when you sign out of Sleeper. Paste a fresh "
            "one to see offers waiting on you."
        )

    pending = [t.to_dict() for t in trades if t.status == "proposed"]
    history = [t.to_dict() for t in trades if t.status != "proposed"][:20]

    if available and context.league.platform == PlatformType.SLEEPER and not token:
        available = False
        notice = (
            "Sleeper's public API only returns completed trades. Connect your "
            "Sleeper token to see offers waiting on you."
        )

    return TradeOffersResponse(
        league_id=league_id,
        platform=context.league.platform.value,
        my_team_id=context.my_team.id if context.my_team else None,
        pending=pending,
        history=history,
        pending_available=available,
        pending_notice=notice,
    )


@router.post("/league/{league_id}/sleeper-token", status_code=status.HTTP_204_NO_CONTENT)
async def connect_sleeper_token(
    league_id: int,
    body: SleeperTokenRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """Store a Sleeper bearer token for this league, encrypted.

    Encrypted at rest with the same Fernet key that protects the ESPN cookies
    on the same row. Only ever read back to ask Sleeper for this league's
    pending trades.
    """
    league = await league_context.load_league(league_id, current_user, db)
    if league.platform != PlatformType.SLEEPER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Sleeper leagues use a Sleeper token",
        )

    league.sleeper_token_encrypted = encrypt_data(body.token.strip())
    await db.commit()
    logger.info("Sleeper token stored", league_id=league_id, user_id=current_user.id)


@router.delete("/league/{league_id}/sleeper-token", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_sleeper_token(
    league_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    league = await league_context.load_league(league_id, current_user, db)
    league.sleeper_token_encrypted = None
    await db.commit()


@router.post("/league/{league_id}/evaluate", response_model=TradeEvaluation)
async def evaluate_trade(
    league_id: int,
    body: TradeEvaluationRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """Score a trade properly: lineup impact, depth, playoff odds, AI read.

    `team_a_id` is treated as "you" throughout. The verdict, the odds delta and
    the AI summary are all written from that team's point of view.
    """
    context = await _load_context(league_id, current_user, db)
    team_a, team_b = context.team(body.team_a_id), context.team(body.team_b_id)
    roster_a, roster_b = context.roster(team_a.id), context.roster(team_b.id)

    a_sends = _players_on(roster_a, body.team_a_sends, team_a.name)
    b_sends = _players_on(roster_b, body.team_b_sends, team_b.name)

    side_a = trade_engine.evaluate_side(
        team_id=team_a.id,
        team_name=team_a.name,
        roster=roster_a,
        outgoing_ids=body.team_a_sends,
        incoming=b_sends,
        slots=context.slots,
        levels=context.levels,
    )
    side_b = trade_engine.evaluate_side(
        team_id=team_b.id,
        team_name=team_b.name,
        roster=roster_b,
        outgoing_ids=body.team_b_sends,
        incoming=a_sends,
        slots=context.slots,
        levels=context.levels,
    )
    fairness = trade_engine.fairness_score(side_a, side_b)

    # Odds and intel are independent lookups, so they run together.
    odds_task = (
        _playoff_odds(context, side_a, side_b) if body.include_odds
        else asyncio.sleep(0, result=None)
    )
    odds, intel = await asyncio.gather(
        odds_task, player_intel.gather(a_sends + b_sends)
    )

    odds_delta = odds.delta if odds else None
    verdict, headline = trade_engine.verdict_label(
        side_a.lineup_delta, odds_delta, fairness
    )
    risks = _risks(a_sends, b_sends, side_a, intel)

    ai_summary, ai_points, counter = None, [], None
    if body.include_ai and llm_service.is_available():
        result = await llm_service.trade_verdict(
            context=_ai_context(
                context, team_a, team_b, a_sends, b_sends, side_a, side_b,
                fairness, odds, verdict, risks, intel,
            )
        )
        ai_summary = result.get("summary")
        points = result.get("points")
        ai_points = [str(p) for p in points][:5] if isinstance(points, list) else []
        counter = result.get("counter") or None

    return TradeEvaluation(
        verdict=verdict,
        headline=headline,
        fairness_score=fairness,
        you=side_a.to_dict(),
        them=side_b.to_dict(),
        playoff_odds=odds,
        risks=risks,
        ai_summary=ai_summary,
        ai_points=ai_points,
        counter_suggestion=counter,
        players_you_send=[trade_feed._brief(p) for p in a_sends],
        players_you_get=[trade_feed._brief(p) for p in b_sends],
        intel=intel,
    )


def _players_on(
    roster: List[dict], player_ids: List[str], team_name: str
) -> List[dict]:
    """Resolve ids against a roster, refusing anything not actually on it.

    A 400 here rather than silently dropping the player: a trade evaluated
    against the wrong set of players is worse than no answer, because it looks
    like an answer.
    """
    index = {str(p.get("player_id")): p for p in roster}
    resolved, missing = [], []
    for pid in player_ids:
        found = index.get(str(pid))
        if found:
            resolved.append(found)
        else:
            missing.append(str(pid))
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not on {team_name}'s roster: {', '.join(missing)}",
        )
    return resolved


async def _playoff_odds(
    context: TradeContext,
    side_a: trade_engine.SideImpact,
    side_b: trade_engine.SideImpact,
) -> Optional[PlayoffOdds]:
    """Run the season twice: as things stand, and as they would be post-trade.

    Only the two trading teams' weekly means change between the runs; everyone
    else is held fixed, so the delta isolates the trade. Both runs share a seed
    so the difference is the trade rather than simulation noise, which matters
    when the true effect is under a point.
    """
    league = context.league
    week = int(league.current_week or 1)
    last_week = _last_regular_week(league)
    if week > last_week:
        return None

    schedule = await trade_feed.remaining_schedule(
        league,
        context.teams,
        from_week=week,
        through_week=last_week,
        cookies=league_context.espn_cookies(league),
    )
    if not schedule:
        return None

    changed = {side_a.team_id: side_a, side_b.team_id: side_b}

    def sim_teams(after: bool) -> List[trade_engine.SimTeam]:
        out = []
        for team in context.teams:
            impact = changed.get(team.id)
            if impact is not None:
                mean = impact.lineup_after if after else impact.lineup_before
            else:
                mean, _ = trade_engine.optimal_lineup(
                    context.roster(team.id), context.slots
                )
            out.append(
                trade_engine.SimTeam(
                    team_id=team.id,
                    name=team.name,
                    wins=float(team.wins or 0),
                    losses=float(team.losses or 0),
                    points_for=float(team.points_for or 0.0),
                    weekly_mean=max(mean, 1.0),
                )
            )
        return out

    spots = _playoff_spots(league)
    seed = 20260916
    before = trade_engine.simulate_season(
        sim_teams(False), schedule, spots, seed=seed
    )
    after = trade_engine.simulate_season(
        sim_teams(True), schedule, spots, seed=seed
    )

    mine_before = before.get(side_a.team_id, 0.0)
    mine_after = after.get(side_a.team_id, 0.0)
    return PlayoffOdds(
        before=mine_before,
        after=mine_after,
        delta=round(mine_after - mine_before, 1),
        iterations=trade_engine.DEFAULT_ITERATIONS,
        weeks_simulated=len(schedule),
        playoff_spots=spots,
        schedule_source="platform",
    )


def _last_regular_week(league: League) -> int:
    raw = (league.roster_settings or {}).get("playoff_week_start")
    try:
        return max(1, int(raw) - 1)
    except (TypeError, ValueError):
        return 14


def _risks(
    outgoing: List[dict],
    incoming: List[dict],
    side: trade_engine.SideImpact,
    intel: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Flags drawn from the data, never guessed.

    Three sources, all of which state their facts rather than infer them: the
    roster payload's injury designation, `player_intel` (depth-chart role,
    injury detail, and headlines the wire itself categorised as injury or
    transaction), and the recomputed depth table. Anything a manager would
    weigh that is not in one of those is absent on purpose.
    """
    flags: List[str] = []
    incoming_ids = [p.get("player_id") for p in incoming]

    if intel:
        flags.extend(player_intel.flags_from_intel(intel, incoming_ids))
    else:
        for player in incoming:
            status_text = (player.get("injury_status") or "").strip()
            if status_text and status_text.upper() not in ("ACTIVE", "NA", "NONE"):
                flags.append(f"{player.get('full_name')} is listed {status_text}.")

    for position, after in side.depth_after.items():
        before = side.depth_before.get(position, {})
        if after["startable"] < after["required"] <= before.get("startable", 0):
            flags.append(
                f"Leaves you short at {position}: "
                f"{after['startable']} startable for {after['required']} slot(s)."
            )
    return flags


def _ai_context(
    context: TradeContext,
    team_a: Team,
    team_b: Team,
    a_sends: List[dict],
    b_sends: List[dict],
    side_a: trade_engine.SideImpact,
    side_b: trade_engine.SideImpact,
    fairness: float,
    odds: Optional[PlayoffOdds],
    verdict: str,
    risks: List[str],
    intel: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """The pre-computed facts handed to the model. Nothing it must derive."""
    return {
        "league": {
            "name": context.league.name,
            "scoring": context.league.scoring_type,
            "teams": len(context.teams),
            "week": context.league.current_week,
            "starting_slots": {
                **context.slots.counts,
                "FLEX": context.slots.flex,
                "SUPER_FLEX": context.slots.superflex,
            },
        },
        "you": {
            "team": team_a.name,
            "record": f"{team_a.wins}-{team_a.losses}",
            "you_send": [trade_feed._brief(p) for p in a_sends],
            "you_receive": [trade_feed._brief(p) for p in b_sends],
            "weekly_lineup_points_before": side_a.lineup_before,
            "weekly_lineup_points_after": side_a.lineup_after,
            "weekly_lineup_change": side_a.lineup_delta,
            "value_over_replacement_given_up": side_a.value_out,
            "value_over_replacement_received": side_a.value_in,
            "position_depth_after": side_a.depth_after,
        },
        "them": {
            "team": team_b.name,
            "record": f"{team_b.wins}-{team_b.losses}",
            "weekly_lineup_change": side_b.lineup_delta,
            "value_over_replacement_received": side_b.value_in,
        },
        "fairness_score_0_100": fairness,
        "playoff_odds": odds.model_dump() if odds else "not simulated",
        "engine_verdict": verdict,
        "data_flags": risks,
        # Real, sourced facts about the players involved: depth-chart role,
        # injury designation and recent tagged headlines. The model may cite
        # these; it may not add to them.
        "player_news": intel or {},
        "note": (
            "Projections are weekly expected points. 'Value over replacement' is "
            "points above a freely available starter at that position in this "
            "league. These numbers are already computed; do not recompute them."
        ),
    }


@router.get("/league/{league_id}/finder", response_model=TradeFinderResponse)
async def find_trades(
    league_id: int,
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """Trades worth proposing: ones that improve both teams' starting lineups.

    A trade only happens if the other manager says yes, so ranking by your own
    gain alone surfaces offers nobody accepts. These are filtered to deals where
    both lineups improve, then sorted by your gain first.
    """
    context = await _load_context(league_id, current_user, db)
    if not context.my_team:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Claim your team in this league to get trade suggestions",
        )

    mine = context.my_team.id
    ideas = trade_engine.find_opportunities(
        my_team_id=mine,
        my_roster=context.roster(mine),
        other_rosters={t.id: context.roster(t.id) for t in context.teams if t.id != mine},
        team_names=context.team_names,
        slots=context.slots,
        levels=context.levels,
        limit=max(1, min(limit, 25)),
    )

    depth = trade_engine.position_depth(
        context.roster(mine), context.slots, context.levels
    )
    needs = [pos for pos, d in depth.items() if d["required"] and d["surplus"] < 0]
    surplus = [pos for pos, d in depth.items() if d["surplus"] > 0]

    return TradeFinderResponse(
        league_id=league_id,
        my_team_id=mine,
        ideas=[i.to_dict() for i in ideas],
        needs=needs,
        surplus=surplus,
    )


@router.get("/league/{league_id}/market")
async def trade_market(
    league_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """Every rostered player with a trade value, plus each team's shape.

    Backs the player pickers in the trade machine, so the UI never has to ask
    anyone for a platform player id again.
    """
    context = await _load_context(league_id, current_user, db)

    teams = []
    for team in context.teams:
        roster = context.roster(team.id)
        depth = trade_engine.position_depth(roster, context.slots, context.levels)
        teams.append({
            "team_id": team.id,
            "team_name": team.name,
            "is_mine": bool(context.my_team and team.id == context.my_team.id),
            "record": f"{team.wins}-{team.losses}",
            "lineup_points": trade_engine.optimal_lineup(roster, context.slots)[0],
            "needs": [p for p, d in depth.items() if d["required"] and d["surplus"] < 0],
            "surplus": [p for p, d in depth.items() if d["surplus"] > 0],
            "players": [
                {
                    **trade_feed._brief(player),
                    "value": trade_engine.value_over_replacement(player, context.levels),
                    "is_starter": bool(player.get("is_starter")),
                    "on_injured_reserve": bool(player.get("on_injured_reserve")),
                }
                for player in sorted(
                    roster, key=trade_engine.player_points, reverse=True
                )
            ],
        })

    return {
        "league_id": league_id,
        "my_team_id": context.my_team.id if context.my_team else None,
        "replacement_levels": context.levels,
        "starting_slots": {
            **context.slots.counts,
            "FLEX": context.slots.flex,
            "SUPER_FLEX": context.slots.superflex,
        },
        "teams": teams,
    }


@router.post("/league/{league_id}/counters", response_model=CounterResponse)
async def explore_counters(
    league_id: int,
    body: CounterRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """Counter-offers worth sending back, ranked, with the reason for each.

    Deliberately its own endpoint rather than a field on the evaluation. The
    point is that the user triggers it and explores, so it runs on demand and
    it runs whatever the verdict was: a trade worth accepting may still be
    worth improving, and a trade worth rejecting is the one most likely to have
    a version you would take.

    Returns an empty list with a plain-language `summary` when nothing beats
    accepting as written. That is an answer, not a failure.
    """
    context = await _load_context(league_id, current_user, db)
    mine, theirs = context.team(body.team_a_id), context.team(body.team_b_id)
    my_roster, their_roster = context.roster(mine.id), context.roster(theirs.id)

    # Validate up front so a typo is a 400 rather than a silently different trade.
    _players_on(my_roster, body.team_a_sends, mine.name)
    _players_on(their_roster, body.team_b_sends, theirs.name)

    base_you = trade_engine.evaluate_side(
        team_id=mine.id, team_name=mine.name, roster=my_roster,
        outgoing_ids=body.team_a_sends,
        incoming=_players_on(their_roster, body.team_b_sends, theirs.name),
        slots=context.slots, levels=context.levels,
    )
    base_them = trade_engine.evaluate_side(
        team_id=theirs.id, team_name=theirs.name, roster=their_roster,
        outgoing_ids=body.team_b_sends,
        incoming=_players_on(my_roster, body.team_a_sends, mine.name),
        slots=context.slots, levels=context.levels,
    )
    base_fairness = trade_engine.fairness_score(base_you, base_them)
    verdict, headline = trade_engine.verdict_label(
        base_you.lineup_delta, None, base_fairness
    )

    counters = trade_engine.counter_offers(
        my_team_id=mine.id,
        their_team_id=theirs.id,
        my_roster=my_roster,
        their_roster=their_roster,
        original_give_ids=body.team_a_sends,
        original_receive_ids=body.team_b_sends,
        slots=context.slots,
        levels=context.levels,
        limit=body.limit,
    )

    if counters:
        # `counters[0]` leads on plausibility, not on gain, so the sentence
        # describes the one a manager would actually send. Its band is named
        # explicitly: when even the best option is a long shot, saying "the
        # most realistic" about it would be the wrong impression.
        best = counters[0]
        plausible = sum(
            1 for c in counters if c.likelihood in ("easy_ask", "fair_ask")
        )
        count = f"{len(counters)} counter{'s' if len(counters) > 1 else ''}"
        if plausible:
            summary = (
                f"{count} beat accepting as written, {plausible} of which "
                f"leave their lineup better off too. The best of those is "
                f"worth {best.gain_vs_original:+.1f} points a week more to you "
                f"than the offer on the table."
            )
        else:
            summary = (
                f"{count} beat accepting as written, but every one of them "
                f"leaves the other team worse off than the deal they proposed, "
                f"so expect to negotiate. The strongest is worth "
                f"{best.gain_vs_original:+.1f} points a week more to you."
            )
    else:
        summary = (
            "Nothing built from these two rosters beats simply accepting or "
            "declining. Every alternative either leaves your starting lineup "
            "worse or asks them for more than the deal they proposed."
        )

    ai_summary = None
    if body.include_ai and counters and llm_service.is_available():
        result = await llm_service.trade_verdict(
            context={
                "task": (
                    "Advise on which counter-offer to send. The counters and "
                    "every number are already computed; pick among them and say "
                    "why in the manager's own terms."
                ),
                "league": {
                    "name": context.league.name,
                    "scoring": context.league.scoring_type,
                    "teams": len(context.teams),
                },
                "offer_on_the_table": {
                    "you_send": [trade_feed._brief(p) for p in
                                 _players_on(my_roster, body.team_a_sends, mine.name)],
                    "you_receive": [trade_feed._brief(p) for p in
                                    _players_on(their_roster, body.team_b_sends, theirs.name)],
                    "your_weekly_lineup_change": base_you.lineup_delta,
                    "engine_verdict": verdict,
                },
                "counters": [c.to_dict() for c in counters],
                "note": (
                    "'gain_vs_original' is weekly points above simply accepting. "
                    "'cost_to_them' is how much worse the counter is than the "
                    "deal they themselves proposed, so it measures how big an "
                    "ask it is. Do not invent players or numbers."
                ),
            }
        )
        ai_summary = result.get("summary")

    return CounterResponse(
        league_id=league_id,
        original_verdict=verdict,
        original_lineup_delta=base_you.lineup_delta,
        original_headline=headline,
        counters=[c.to_dict() for c in counters],
        summary=summary,
        ai_summary=ai_summary,
    )

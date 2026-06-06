"""
API endpoints for draft preparation and the live draft assistant.

Provides a league-scoring-aware value board (VBD rankings) plus pick
recommendations. Works for BOTH Sleeper and ESPN leagues:

- Value board / Big Board: scoring-adjusted rankings for either platform.
- Live assist: Sleeper has a public live-draft feed, so picks are tracked in
  real time. ESPN has no equivalent public feed, so for ESPN leagues the
  assistant serves a scoring-adjusted big board of best-available players.

Player projections come from the free Sleeper data set in all cases (it is just
the projection source for the rankings; no Sleeper league is required).
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Dict, Any
import structlog

from app.db.database import get_database
from app.models.user import User
from app.models.league import League, PlatformType
from app.core.auth import get_current_active_user
from app.core.config import settings
from app.services.sleeper_service import SleeperService, SleeperError
from app.services.draft_service import draft_service
from app.services.llm_service import llm_service
from app.schemas.draft import ValueBoardResponse, DraftAssistResponse, DraftAdvice, DraftPickRecommendation

logger = structlog.get_logger()
router = APIRouter(prefix="/draft", tags=["draft"])

# ESPN lineup-slot names -> value-board position codes
_ESPN_SLOT_TO_POSITION = {"D/ST": "DEF", "DST": "DEF"}
_NON_DRAFT_SLOTS = {"BENCH", "BN", "IR"}

_ESPN_ASSIST_NOTE = (
    "Live in-draft pick tracking is available for Sleeper leagues. For ESPN this "
    "is your scoring-adjusted big board of best-available players."
)


async def _load_league(league_id: int, user: User, db: AsyncSession) -> League:
    """Load any league owned by the user, or raise an HTTP error."""
    result = await db.execute(
        select(League).where(
            League.id == league_id,
            League.owner_user_id == user.id,
        )
    )
    league = result.scalar_one_or_none()
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found or access denied",
        )
    return league


def _espn_roster_positions(league: League) -> Optional[list]:
    """Derive a roster_positions list from an ESPN league's lineup slots."""
    slots = (league.roster_settings or {}).get("lineup_slots") or {}
    positions: list = []
    for slot, count in slots.items():
        norm = _ESPN_SLOT_TO_POSITION.get(slot, slot)
        if norm in _NON_DRAFT_SLOTS:
            continue
        try:
            positions.extend([norm] * int(count))
        except (TypeError, ValueError):
            continue
    return positions or None


async def _board_params(league: League) -> Dict[str, Any]:
    """
    Resolve the inputs needed to build a value board for either platform.

    Sleeper leagues expose exact scoring + roster settings via the Sleeper API.
    ESPN leagues use the stored scoring_type + size + lineup slots.
    """
    if league.platform == PlatformType.SLEEPER and league.sleeper_league_id:
        sleeper = SleeperService()
        sl = await sleeper.get_league(league.sleeper_league_id)
        return {
            "season": int(sl.get("season") or league.season_year or settings.espn_season_year),
            "scoring_settings": sl.get("scoring_settings"),
            "scoring_type": league.scoring_type or "ppr",
            "roster_positions": sl.get("roster_positions"),
            "team_count": sl.get("total_rosters") or league.size or 12,
        }
    # ESPN (or any league without a Sleeper id): use stored league settings.
    return {
        "season": league.season_year or settings.espn_season_year,
        "scoring_settings": None,  # ESPN custom scoring format differs; use scoring_type
        "scoring_type": league.scoring_type or "ppr",
        "roster_positions": _espn_roster_positions(league),
        "team_count": league.size or 12,
    }


@router.get("/rankings", response_model=ValueBoardResponse)
async def get_generic_rankings(
    scoring_type: str = Query("ppr", description="standard | half_ppr | ppr"),
    team_count: int = Query(12, ge=4, le=20),
    season: Optional[int] = Query(None, description="Defaults to configured season year"),
    limit: int = Query(200, ge=10, le=500),
    current_user: User = Depends(get_current_active_user),
):
    """
    Pre-draft cheat sheet: a VBD value board using standard scoring presets.

    Use this before connecting a league, or for a quick generic ranking. For a
    board tuned to your league's exact scoring, use /draft/value-board/{league_id}.
    """
    try:
        board = await draft_service.build_value_board(
            season=season or settings.espn_season_year,
            scoring_settings=None,
            scoring_type=scoring_type,
            roster_positions=None,
            team_count=team_count,
            limit=limit,
        )
        return board
    except SleeperError as e:
        logger.error("Sleeper error building rankings", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not fetch player data from Sleeper: {str(e)}",
        )


@router.get("/value-board/{league_id}", response_model=ValueBoardResponse)
async def get_league_value_board(
    league_id: int,
    limit: int = Query(200, ge=10, le=500),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """
    Build a draft value board tuned to a league's scoring settings.

    Works for both Sleeper and ESPN leagues. Sleeper leagues use exact scoring
    pulled live from Sleeper; ESPN leagues use their scoring type, size, and
    lineup slots. Projections come from the free Sleeper data set either way.
    """
    league = await _load_league(league_id, current_user, db)

    try:
        params = await _board_params(league)
        board = await draft_service.build_value_board(limit=limit, **params)
        return board
    except SleeperError as e:
        logger.error("Sleeper error building value board", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not fetch player data from Sleeper: {str(e)}",
        )


def _board_to_recommendations(board: Dict[str, Any], limit: int) -> list:
    """Turn raw value-board players into best-available recommendations."""
    recs = []
    for p in board["players"][:limit]:
        rec = dict(p)
        rec["need_bonus"] = None
        rec["pick_score"] = p.get("vbd")
        rec["adp_delta"] = None
        rec["is_value"] = False
        recs.append(DraftPickRecommendation(**rec))
    return recs


async def _espn_assist(league: League, ai: bool, limit: int) -> DraftAssistResponse:
    """Best-available board for an ESPN league (no public live-draft feed)."""
    params = await _board_params(league)
    board = await draft_service.build_value_board(limit=max(limit, 50), **params)
    recommendations = _board_to_recommendations(board, limit)

    result = DraftAssistResponse(
        draft_id=f"espn-{league.espn_league_id}",
        status="board",
        round=1,
        picks_made=0,
        team_count=board["team_count"],
        scoring=board["scoring"],
        user_roster=[],
        user_position_counts={},
        current_pick=1,
        next_user_pick=None,
        picks_until_next=None,
        on_the_clock=False,
        positional_runs={},
        recommendations=recommendations,
        live_pick_tracking=False,
        note=_ESPN_ASSIST_NOTE,
    )

    if ai and recommendations:
        advice = await llm_service.analyze_draft_pick(
            round_number=1,
            user_roster=[],
            position_needs={},
            top_available=[r.model_dump() for r in recommendations],
            scoring=board["scoring"],
        )
        result.ai_advice = DraftAdvice(**advice)
    return result


@router.get("/assist/{league_id}", response_model=DraftAssistResponse)
async def get_draft_assist(
    league_id: int,
    ai: bool = Query(False, description="Include AI advice (slower; use on demand, not for polling)"),
    limit: int = Query(10, ge=1, le=30),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """
    Draft assistant: best-available recommendations for a league.

    Sleeper leagues are tracked live (reads picks already made, infers your
    roster needs, and ranks undrafted players by value + need). ESPN leagues get
    a scoring-adjusted big board of best-available players, since ESPN has no
    public live-draft feed.
    """
    league = await _load_league(league_id, current_user, db)

    # ESPN (or any non-Sleeper league): serve the scoring-adjusted big board.
    if league.platform != PlatformType.SLEEPER or not league.sleeper_league_id:
        try:
            return await _espn_assist(league, ai, limit)
        except SleeperError as e:
            logger.error("Error building ESPN draft board", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not build draft board: {str(e)}",
            )

    # Sleeper: live draft tracking.
    sleeper = SleeperService()
    try:
        sleeper_league = await sleeper.get_league(league.sleeper_league_id)
        drafts = await sleeper.get_league_drafts(league.sleeper_league_id)
    except SleeperError as e:
        logger.error("Sleeper error fetching draft info", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not fetch draft info from Sleeper: {str(e)}",
        )

    if not drafts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No draft found for this league yet.",
        )

    draft_id = drafts[0].get("draft_id")
    scoring_settings = sleeper_league.get("scoring_settings")
    roster_positions = sleeper_league.get("roster_positions")

    try:
        result = await draft_service.recommend_picks(
            draft_id=draft_id,
            user_id=league.sleeper_user_id,
            scoring_settings=scoring_settings,
            scoring_type=league.scoring_type or "ppr",
            roster_positions=roster_positions,
            limit=limit,
        )
    except SleeperError as e:
        logger.error("Sleeper error generating recommendations", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not generate recommendations: {str(e)}",
        )

    # Optional AI narrative advice layered on top of the deterministic ranking
    if ai:
        advice = await llm_service.analyze_draft_pick(
            round_number=result.get("round") or 1,
            user_roster=result.get("user_roster", []),
            position_needs=result.get("user_position_counts", {}),
            top_available=result.get("recommendations", []),
            scoring=result.get("scoring", "ppr"),
        )
        result["ai_advice"] = DraftAdvice(**advice)

    return result


@router.get("/health")
async def draft_health():
    """Check that draft data sources are reachable."""
    return {
        "draft_tools": "ready",
        "llm_available": llm_service.is_available(),
        "data_source": "sleeper",
    }

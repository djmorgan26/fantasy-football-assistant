"""The plan: what to do about your roster, in the order it matters.

A manager opening the app after a starter lands on IR has four questions, and
until now the app answered none of them: who covers the slot this week, who is
available to replace him properly, what should I bid, and is there a trade in
the mess this leaves. Answering only the first is what makes an app something
you check rather than something you use.

Every recommendation is assembled from real roster, free-agent, budget and
league data first. The prose is written last, over those numbers, so it has
something to quote and nothing to invent.
"""
import asyncio
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.db.database import get_database
from app.models.league import League, PlatformType
from app.models.team import Team
from app.models.user import User
from app.services import action_plan, league_context, news_service
from app.services.llm_service import llm_service

logger = structlog.get_logger()
router = APIRouter(prefix="/actions", tags=["actions"])


async def _free_agents(league: League, position: Optional[str]) -> List[Dict[str, Any]]:
    """The available pool, in one shape whichever platform the league is on."""
    try:
        if league.platform == PlatformType.SLEEPER and league.sleeper_league_id:
            from app.services.sleeper_service import get_free_agents

            return await get_free_agents(league.sleeper_league_id, position=position, limit=40)

        if league.espn_league_id:
            from app.services.espn_service import ESPNService

            raw = await ESPNService().get_available_players(
                str(league.espn_league_id),
                week=league.current_week,
                position=position,
                cookies=league_context.espn_cookies(league),
            )
            return [
                {
                    "player_id": p.get("player_id"),
                    "full_name": p.get("full_name"),
                    "position_name": p.get("position_name"),
                    "pro_team_abbr": p.get("pro_team_abbr"),
                    "projected_points": p.get("projected_points") or 0,
                    "injury_status": p.get("injury_status"),
                }
                for p in raw or []
            ]
    except Exception as e:
        # A missing waiver pool degrades the plan; it must not lose the lineup
        # advice, which is the part that matters most and needs no network.
        logger.warning("Could not load free agents", league_id=league.id, error=str(e))
    return []


async def _my_budget(league: League, team: Team) -> Dict[str, Optional[float]]:
    """This team's FAAB, if the league uses it."""
    try:
        if league.platform == PlatformType.SLEEPER and league.sleeper_league_id:
            from app.services.sleeper_service import get_waiver_budgets

            budgets = await get_waiver_budgets(league.sleeper_league_id)
            key = team.sleeper_roster_id
            mine = next((b for b in budgets if b.get("team_id") == key), None)
        elif league.espn_league_id:
            from app.services.espn_service import ESPNService

            budgets = await ESPNService().get_waiver_budgets(
                str(league.espn_league_id), cookies=league_context.espn_cookies(league)
            )
            mine = next(
                (b for b in budgets if b.get("team_id") == team.espn_team_id), None
            )
        else:
            mine = None

        if mine:
            return {
                "remaining": mine.get("current_budget"),
                "total": mine.get("total_budget"),
            }
    except Exception as e:
        logger.warning("Could not load waiver budget", league_id=league.id, error=str(e))
    return {"remaining": None, "total": None}


async def _rival_depth(
    league: League, me: Team, db: AsyncSession
) -> List[Dict[str, Any]]:
    """Every other team's positional depth, for finding a trade partner."""
    teams = [t for t in await league_context.all_teams(league, db) if t.id != me.id]

    async def one(team: Team) -> Optional[Dict[str, Any]]:
        try:
            roster = await league_context.roster_for(league, team)
        except Exception:
            return None
        if not roster:
            return None
        return {"team": team.name, "depth": action_plan.positional_depth(roster)}

    return [r for r in await asyncio.gather(*(one(t) for t in teams)) if r]


@router.get("/{league_id}")
async def action_plan_for_league(
    league_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    """Everything worth doing about this roster, ranked."""
    league = await league_context.load_league(league_id, current_user, db)
    team = await league_context.my_team(league, current_user, db)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim your team in this league to get a plan for it.",
        )

    roster = await league_context.roster_for(league, team)
    if not roster:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not read your roster from the platform just now.",
        )

    holes = action_plan.find_holes(roster)
    risks = action_plan.find_risks(roster)
    depth = action_plan.positional_depth(roster)

    # The positions that actually need outside help decide what to fetch, so a
    # healthy roster costs one roster read and nothing else.
    needed = {h["position"] for h in holes if h.get("position")}

    free_agents, budget, trending_raw, rivals = await asyncio.gather(
        _free_agents(league, None) if needed else _nothing(),
        _my_budget(league, team),
        _trending(),
        _rival_depth(league, me=team, db=db) if needed else _nothing(),
    )
    trending = {t["name"]: t.get("count", 0) for t in trending_raw}

    plan: List[Dict[str, Any]] = []
    for hole in holes:
        bench = action_plan.bench_options(hole, roster)
        best = bench[0] if bench else None
        urgency = action_plan.urgency_for(hole, best)
        waivers = action_plan.waiver_options(hole, free_agents, trending)

        plan.append({
            "kind": "lineup_hole",
            "urgency": urgency,
            "hole": hole,
            "start_instead": best,
            "other_bench": bench[1:3],
            "waiver_targets": waivers,
            "faab": action_plan.faab_advice(
                budget["remaining"], budget["total"], urgency
            ),
            "trades": action_plan.trade_angles(depth, rivals, hole.get("position")),
        })

    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    plan.sort(key=lambda a: order.get(a["urgency"], 9))

    summary = await _write_summary(league, team, plan, risks)

    return {
        "league_id": league.id,
        "league": league.name,
        "team": team.name,
        "week": league.current_week or 1,
        "summary": summary,
        "actions": plan,
        "risks": risks,
        "depth": depth,
        "budget": budget,
        "all_clear": not plan and not risks,
    }


async def _nothing() -> List[Dict[str, Any]]:
    return []


async def _trending() -> List[Dict[str, Any]]:
    try:
        return await news_service.fetch_trending(limit=25)
    except Exception:
        return []


async def _write_summary(
    league: League,
    team: Team,
    plan: List[Dict[str, Any]],
    risks: List[Dict[str, Any]],
) -> Optional[str]:
    """Two or three sentences over the facts already computed.

    The model is given the finished analysis and told to explain it, not to do
    it. Everything it can say is in the block above it, which is what keeps it
    from inventing a player who is not on the roster.
    """
    if not plan and not risks:
        return None

    lines = [f"Team: {team.name}. League: {league.name}. Week {league.current_week or 1}."]
    for action in plan:
        hole = action["hole"]
        lines.append(
            f"- {hole['player']} ({hole['position']}, {hole['slot']}) is "
            f"{hole['status']}: that slot scores 0. Urgency {action['urgency']}."
        )
        if action["start_instead"]:
            b = action["start_instead"]
            lines.append(
                f"  Best bench cover: {b['player']} ({b['position']}), "
                f"projected {b['projected']}, scored {b['last_week']} last week."
            )
        else:
            lines.append("  No bench player is eligible for that slot.")
        for w in action["waiver_targets"][:3]:
            lines.append(
                f"  Available: {w['player']} ({w['position']}, {w['team']}), "
                f"projected {w['projected']}"
                + (f", added in {w['added_by']} leagues today" if w["contested"] else "")
            )
        if action["faab"]:
            f = action["faab"]
            lines.append(
                f"  FAAB: ${f['remaining']} of ${f['total']} left; "
                f"suggested bid ${f['suggested_bid']}."
            )
        for t in action["trades"]:
            lines.append(
                f"  {t['team']} is thin at {t['they_need']} and can spare "
                f"{t['they_can_spare']}."
            )
    for r in risks:
        lines.append(f"- {r['player']} is {r['status']} in the {r['slot']} slot.")

    facts = "\n".join(lines)
    prompt = f"""{facts}

Write 2-3 sentences telling this manager what to do first and why.

HARD RULES:
- Use only the facts above. Every player, number and team name must appear in
  them. If it is not there, it did not happen.
- Do not invent injuries, projections, opponents or managers' real names.
- Lead with the single most urgent action.

FORMAT: plain text, no markdown, no bullets, no bold."""

    try:
        # complete() is a blocking Groq call; off-thread so it does not stall
        # the event loop for the length of a generation.
        return await asyncio.to_thread(
            llm_service.complete,
            system="You are a fantasy football assistant. You are blunt, specific "
                   "and you never invent a fact.",
            prompt=prompt,
            temperature=0.6,
            # Generous on purpose: the model reasons before it answers and that
            # reasoning is billed against this budget, so a tight ceiling
            # truncates the reply rather than shortening it.
            max_tokens=800,
            purpose="action_plan",
        )
    except Exception as e:
        logger.warning("Action plan summary unavailable", error=str(e))
        return None

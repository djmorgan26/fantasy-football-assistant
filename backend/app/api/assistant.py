"""
The Commissioner: a league-aware chat assistant, and the weekly primer.

The difference between this and every other fantasy chatbot is the same
difference that runs through the whole app — it knows the *league*, not just
your roster, and it answers in the league's own voice rather than a product's.

Grounding follows the house rule: gather real facts first, hand them to the
model, and forbid it from going beyond them. See content_service.
"""
import asyncio
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.db.database import get_database
from app.models.board import BoardPost
from app.models.league import League, PlatformType
from app.models.team import Team
from app.models.user import User
from app.services import board_service, league_context, news_service
from app.services.content_service import DEFAULT_VOICE, content_service
from app.services.llm_service import llm_service

logger = structlog.get_logger()
router = APIRouter(prefix="/assistant", tags=["assistant"])

UNAVAILABLE = (
    "The AI writer is not configured right now, so I can't answer that one. "
    "Add a GROQ_API_KEY and I'll have plenty to say."
)


class ChatTurn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: List[ChatTurn] = Field(default_factory=list, max_length=12)


class ChatResponse(BaseModel):
    reply: str
    generated_by: str
    grounded_on: List[str] = []






def _roster_lines(roster: List[dict]) -> str:
    lines = []
    for p in roster:
        slot = p.get("lineup_slot_name") or p.get("position_name") or "?"
        flag = f" [{p['injury_status']}]" if p.get("injury_status") else ""
        lines.append(
            f"  {slot:<6} {p.get('full_name','?')} ({p.get('position_name','?')}, "
            f"{p.get('pro_team_abbr') or 'FA'}) "
            f"proj {p.get('projected_points') or 0:.1f}, scored {p.get('applied_points') or 0:.1f}{flag}"
        )
    return "\n".join(lines)


async def _standings(league: League, db: AsyncSession) -> str:
    teams = (await db.execute(
        select(Team).where(Team.league_id == league.id)
    )).scalars().all()
    ranked = sorted(teams, key=lambda t: (-(t.wins or 0), -(t.points_for or 0)))
    return "\n".join(
        f"  {i}. {t.name} ({t.wins}-{t.losses}"
        f"{'-' + str(t.ties) if t.ties else ''}), {t.points_for:.1f} PF"
        for i, t in enumerate(ranked, 1)
    )


async def _build_context(
    league: League, user: User, db: AsyncSession
) -> tuple[str, List[str]]:
    """Everything the model is allowed to know, and a list of what we gave it."""
    sources: List[str] = []
    blocks: List[str] = [
        f"LEAGUE: {league.name} — {league.size} teams, {league.scoring_type} scoring, "
        f"week {league.current_week} of the {league.season_year} season."
    ]
    sources.append("league settings")

    standings = await _standings(league, db)
    if standings:
        blocks.append(f"STANDINGS:\n{standings}")
        sources.append("standings")

    team = await league_context.my_team(league, user, db)
    if team:
        blocks.append(
            f"THE PERSON ASKING owns '{team.name}' "
            f"({team.wins}-{team.losses}, {team.points_for:.1f} PF)."
        )
        roster = await league_context.roster_for(league, team)
        if roster:
            starters = [p for p in roster if p.get("is_starter")]
            bench = [p for p in roster if not p.get("is_starter")]
            blocks.append("THEIR STARTERS:\n" + _roster_lines(starters))
            blocks.append("THEIR BENCH:\n" + _roster_lines(bench))
            sources.append("your roster")

    try:
        narrative = await _narrative(league)
        if narrative:
            blocks.append("THIS WEEK'S RESULTS:\n" + _facts(narrative))
            sources.append("week results")
    except Exception as e:
        logger.warning("Narrative unavailable for assistant", error=str(e))

    trending = await news_service.fetch_trending(limit=8)
    if trending:
        blocks.append(
            "MOST-ADDED PLAYERS ACROSS FANTASY IN THE LAST 24H:\n"
            + "\n".join(
                f"  {p['name']} ({p.get('position')}, {p.get('team') or 'FA'}) — "
                f"{p['count']:,} adds" for p in trending
            )
        )
        sources.append("waiver trends")

    return "\n\n".join(blocks), sources


async def _narrative(league: League) -> Optional[dict]:
    week = max((league.current_week or 1) - 1, 1)
    if league.platform == PlatformType.SLEEPER and league.sleeper_league_id:
        return await content_service.get_weekly_narrative(league.sleeper_league_id, week)
    if league.espn_league_id:
        return await content_service.get_weekly_narrative_espn(
            str(league.espn_league_id), week, league_context.espn_cookies(league)
        )
    return None


def _facts(narrative: dict) -> str:
    lines = []
    for key, label in (
        ("highest_scorer", "Top scorer"),
        ("lowest_scorer", "Low scorer"),
        ("biggest_blowout", "Biggest blowout"),
        ("closest_game", "Closest game"),
        ("bench_blunder", "Bench blunder"),
    ):
        item = narrative.get(key)
        if isinstance(item, dict):
            lines.append(f"  {label}: " + ", ".join(f"{k}={v}" for k, v in item.items()))
    return "\n".join(lines)


async def _voice(db: AsyncSession, league_id: int) -> str:
    """The league's house voice, plus real style anchors from the board."""
    from app.models.content_profile import LeagueContentProfile

    profile = (await db.execute(
        select(LeagueContentProfile).where(LeagueContentProfile.league_id == league_id)
    )).scalar_one_or_none()

    guide = (profile.voice_guide if profile else None) or DEFAULT_VOICE
    parts = [f"LEAGUE VOICE — write like this, not like a product:\n{guide}"]

    examples = await board_service.get_voice_examples(db, league_id, limit=2)
    if examples:
        parts.append(
            "HOW THIS LEAGUE ACTUALLY TALKS (their own posts, rated highest by the group):\n"
            + "\n\n".join(f'"{e["text"]}"' for e in examples)
        )
    return "\n\n".join(parts)


@router.get("/{league_id}/suggestions")
async def prompt_suggestions(
    league_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """Starter questions, built from this league's actual state.

    Generic chips ("ask me anything") get ignored. Chips naming your real
    opponent and a real player on your bench get tapped.
    """
    league = await league_context.load_league(league_id, current_user, db)
    chips: List[str] = ["Who should I start this week?"]

    team = await league_context.my_team(league, current_user, db)
    if team:
        roster = await league_context.roster_for(league, team)
        bench = [p for p in roster if not p.get("is_starter")]
        if bench:
            best_bench = max(bench, key=lambda p: p.get("projected_points") or 0)
            chips.append(f"Should I start {best_bench.get('full_name')}?")
        hurt = [p for p in roster if p.get("injury_status")]
        if hurt:
            chips.append(f"How bad is the {hurt[0].get('full_name')} injury for me?")

    others = (await db.execute(
        select(Team).where(Team.league_id == league.id, Team.owner_user_id.is_(None)).limit(1)
    )).scalars().first()
    if others:
        chips.append(f"Talk me through a trade with {others.name}")

    trending = await news_service.fetch_trending(limit=1)
    if trending:
        chips.append(f"Is {trending[0]['name']} worth a waiver claim?")

    return {"suggestions": chips[:5]}


@router.post("/{league_id}/chat", response_model=ChatResponse)
async def chat(
    league_id: int,
    payload: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    league = await league_context.load_league(league_id, current_user, db)

    if not llm_service.is_available():
        return {"reply": UNAVAILABLE, "generated_by": "unavailable", "grounded_on": []}

    context, sources = await _build_context(league, current_user, db)
    voice = await _voice(db, league_id)

    history = "\n".join(
        f"{'Them' if t.role == 'user' else 'You'}: {t.content}" for t in payload.history[-6:]
    )

    prompt = (
        f"{voice}\n\n"
        f"WHAT YOU KNOW ABOUT THIS LEAGUE (everything below is real; use nothing else):\n"
        f"{context}\n\n"
        + (f"CONVERSATION SO FAR:\n{history}\n\n" if history else "")
        + f"THEY ASK: {payload.message}\n\n"
        "Answer in 2-4 sentences. Name real teams and real players from the data above. "
        "If the data doesn't cover something, say so plainly instead of guessing — a made-up "
        "stat is worse than an admission. No bullet lists, no headings, just talk."
    )

    try:
        reply = await asyncio.to_thread(
            llm_service.complete,
            system=(
                "You are the commissioner of a fantasy football league and you know everyone in "
                "it. You are funny, blunt, and specific. You never invent statistics."
            ),
            prompt=prompt,
            temperature=0.75,
            # See the note in llm_service.complete: reasoning tokens come out
            # of this budget, so a tight ceiling truncates to nothing.
            max_tokens=1200,
            purpose="commissioner_chat",
        )
        generated_by = llm_service.model
    except Exception as e:
        logger.error("Commissioner chat failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI is having a moment. Try again in a second.",
        )

    return {"reply": reply.strip(), "generated_by": generated_by, "grounded_on": sources}




@router.get("/{league_id}/primer")
async def weekly_primer(
    league_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """Your week in one card: lineup risk, the call that matters, the matchup.

    Everything here is computed, not generated — the one AI touch is the closing
    line of trash talk, and the card reads fine without it.
    """
    league = await league_context.load_league(league_id, current_user, db)
    team = await league_context.my_team(league, current_user, db)
    if not team:
        raise HTTPException(status_code=400, detail="Claim your team first to get a primer.")

    week = league.current_week or 1
    roster = await league_context.roster_for(league, team)

    starters = [p for p in roster if p.get("is_starter")]
    bench = [p for p in roster if not p.get("is_starter") and not p.get("on_injured_reserve")]

    unavailable = {"OUT", "INJURY_RESERVE", "IR", "SUSPENSION"}
    doubtful = {"DOUBTFUL", "QUESTIONABLE"}

    alerts = [
        {
            "player": p.get("full_name"),
            "slot": p.get("lineup_slot_name"),
            "status": p.get("injury_status"),
            "severity": "out" if p.get("injury_status") in unavailable else "questionable",
        }
        for p in starters
        if p.get("injury_status") in (unavailable | doubtful)
    ]

    # The single most valuable swap available: the bench player who most
    # out-projects a starter he could actually replace.
    flex_eligible = {"RB", "WR", "TE"}
    best_swap = None
    for b in bench:
        if b.get("injury_status") in unavailable:
            continue
        replaceable = [
            s for s in starters
            if s.get("position_name") == b.get("position_name")
            or (s.get("lineup_slot_name") == "FLEX" and b.get("position_name") in flex_eligible)
        ]
        if not replaceable:
            continue
        weakest = min(replaceable, key=lambda s: s.get("projected_points") or 0)
        gain = (b.get("projected_points") or 0) - (weakest.get("projected_points") or 0)
        if gain > 0.5 and (best_swap is None or gain > best_swap["gain"]):
            best_swap = {
                "start": b.get("full_name"),
                "sit": weakest.get("full_name"),
                "slot": weakest.get("lineup_slot_name"),
                "gain": round(gain, 1),
            }

    projected = sum(p.get("projected_points") or 0 for p in starters)

    opponent_team = await league_context.opponent_this_week(league, team, week, db)
    opponent = opponent_team.name if opponent_team else None

    trash_talk = None
    if llm_service.is_available() and opponent:
        try:
            voice = await _voice(db, league_id)
            trash_talk = await asyncio.to_thread(
                llm_service.complete,
                system="You write one line of fantasy football trash talk. One sentence. No preamble.",
                prompt=(
                    f"{voice}\n\n"
                    f"'{team.name}' plays '{opponent}' in week {week} and is projected for "
                    f"{projected:.1f} points. Write ONE sentence of trash talk aimed at "
                    f"{opponent}. One sentence only."
                ),
                temperature=0.9,
                max_tokens=800,
                purpose="primer_trash_talk",
            )
            trash_talk = trash_talk.strip().strip('"')
        except Exception as e:
            logger.warning("Primer trash talk failed", error=str(e))

    return {
        "week": week,
        "team_name": team.name,
        "record": f"{team.wins}-{team.losses}" + (f"-{team.ties}" if team.ties else ""),
        "opponent": opponent,
        "projected": round(projected, 1),
        "starters": len(starters),
        "alerts": alerts,
        "best_swap": best_swap,
        "trash_talk": trash_talk,
    }

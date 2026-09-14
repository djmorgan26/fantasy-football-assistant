"""
Weekly League Recap API - Generates hilarious, brutal AI summaries
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_database
from app.models.user import User
from app.models.league import League, PlatformType
from app.core.auth import get_current_active_user
from app.services.espn_service import ESPNService, ESPNCookies, ESPNError
from app.services.sleeper_service import SleeperService, SleeperError
from app.services.llm_service import llm_service
from app.utils.encryption import ESPNCredentialManager
from app.services.league_access import visible_to
import structlog
from typing import Dict, Any, List

logger = structlog.get_logger()
router = APIRouter(prefix="/recap", tags=["recap"])


async def get_espn_weekly_data(league: League, week: int, cookies: ESPNCookies = None) -> Dict[str, Any]:
    """Get ESPN weekly matchup and performance data"""
    espn_service = ESPNService()

    try:
        # Get matchups for the week
        matchups = await espn_service.get_matchups(
            str(league.espn_league_id),
            week=week,
            cookies=cookies
        )

        # Get teams
        teams = await espn_service.get_teams(
            str(league.espn_league_id),
            cookies=cookies
        )

        return {
            "matchups": matchups,
            "teams": teams,
            "platform": "ESPN"
        }
    except ESPNError as e:
        logger.error("ESPN error fetching weekly data", error=str(e))
        raise


async def get_sleeper_weekly_data(league: League, week: int) -> Dict[str, Any]:
    """Get Sleeper weekly matchup and performance data"""
    sleeper_service = SleeperService()

    try:
        # Get matchups for the week
        matchups = await sleeper_service.get_matchups(league.sleeper_league_id, week)

        # Get rosters
        rosters = await sleeper_service.get_rosters(league.sleeper_league_id)

        # Get league users
        users = await sleeper_service.get_league_users(league.sleeper_league_id)

        return {
            "matchups": matchups,
            "rosters": rosters,
            "users": users,
            "platform": "Sleeper"
        }
    except SleeperError as e:
        logger.error("Sleeper error fetching weekly data", error=str(e))
        raise


def build_recap_lines(week: int, weekly_data: Dict[str, Any]) -> List[str]:
    """One factual line per matchup, built only from what the platform returned.

    Returns an empty list when no matchup could be resolved. Callers must treat
    that as "no recap is possible" rather than prompting anyway: an LLM handed a
    heading with no rows under it will happily invent teams and scores.
    """

    platform = weekly_data.get("platform", "Unknown")
    lines: List[str] = []

    if platform == "ESPN":
        matchups = weekly_data.get("matchups", [])
        teams_dict = {team["id"]: team for team in weekly_data.get("teams", [])}

        def describe(team_id, score, projected):
            """'Name (12.3 pts, 4-1, projected 118.4)' from the team row we hold."""
            team = teams_dict.get(team_id)
            if not team:
                return None
            parts = [f"{float(score or 0):.1f} pts"]
            record = f"{team.get('wins', 0)}-{team.get('losses', 0)}"
            if team.get("ties"):
                record += f"-{team['ties']}"
            parts.append(record)
            if projected:
                parts.append(f"projected {float(projected):.1f}")
            return f"{team.get('name', 'Unknown')} ({', '.join(parts)})"

        for matchup in matchups:
            home = describe(
                matchup.get("home_team_id"),
                matchup.get("home_score"),
                matchup.get("home_projected_score"),
            )
            away = describe(
                matchup.get("away_team_id"),
                matchup.get("away_score"),
                matchup.get("away_projected_score"),
            )
            # A bye week has no opponent, and an unknown team id means we cannot
            # name it honestly. Skip both rather than write "Unknown" into the prompt.
            if not home or not away:
                continue

            home_score = float(matchup.get("home_score") or 0)
            away_score = float(matchup.get("away_score") or 0)
            margin = abs(home_score - away_score)
            if matchup.get("winner", "UNDECIDED") in (None, "UNDECIDED"):
                status_text = f"IN PROGRESS, {margin:.1f} apart so far"
            elif margin == 0:
                status_text = "TIED"
            else:
                status_text = f"final, won by {margin:.1f}"
            playoff = " [playoff]" if matchup.get("is_playoff") else ""
            lines.append(f"- {home} vs {away} ({status_text}){playoff}")

    elif platform == "Sleeper":
        matchups = weekly_data.get("matchups", [])
        rosters = weekly_data.get("rosters", [])
        users = weekly_data.get("users", [])

        # Group matchups by matchup_id
        matchup_groups = {}
        for m in matchups:
            mid = m.get("matchup_id")
            if mid not in matchup_groups:
                matchup_groups[mid] = []
            matchup_groups[mid].append(m)

        # Build roster/user lookup
        roster_owners = {}
        for roster in rosters:
            roster_id = roster.get("roster_id")
            owner_id = roster.get("owner_id")
            user = next((u for u in users if u.get("user_id") == owner_id), None)
            roster_owners[roster_id] = user.get("display_name", f"Team {roster_id}") if user else f"Team {roster_id}"

        for matchup_id, teams in matchup_groups.items():
            if len(teams) != 2:
                continue
            team1, team2 = teams[0], teams[1]
            name1 = roster_owners.get(team1.get("roster_id"))
            name2 = roster_owners.get(team2.get("roster_id"))
            if not name1 or not name2:
                continue
            score1 = float(team1.get("points") or 0)
            score2 = float(team2.get("points") or 0)
            margin = abs(score1 - score2)
            status_text = "TIED" if margin == 0 else f"won by {margin:.1f}"
            lines.append(
                f"- {name1} ({score1:.1f} pts) vs {name2} ({score2:.1f} pts) ({status_text})"
            )

    return lines


def build_recap_prompt(league_name: str, week: int, lines: List[str]) -> str:
    """Build a prompt for a weekly recap that stays inside the supplied facts."""

    matchup_text = "MATCHUP RESULTS (the complete and only record of this week):\n" + "\n".join(lines)

    prompt = f"""You are a brutally honest, hilarious fantasy football analyst writing the weekly recap for "{league_name}" Week {week}.

{matchup_text}

FACTUAL RULES - these override every style instruction below:
- The list above is everything you know about this week. It is complete.
- Use ONLY those team names, spelled exactly as written. Never invent a team, a
  manager, or an owner's name.
- Every score, margin and record you state must appear verbatim above. Do not
  compute standings, streaks or season totals that are not written there.
- You have NO player-level data. Never name a quarterback, running back, kicker
  or any other player, and never describe what a player did. Roast the managers
  and the scores instead.
- A matchup marked IN PROGRESS is still being played. Talk about it as unfinished
  and never declare a winner or a final margin for it.
- If something is not in the list, it did not happen. Leave it out.

FORMAT:
- Plain prose in paragraphs separated by a blank line. The card renders your
  reply as raw text, so markdown does not format, it just shows up as literal
  asterisks and hashes. No **bold**, no headings, no bullet lists.

Write an entertaining 3-4 paragraph weekly recap that:

1. **ROASTS THE LOSERS** - Be creative and funny about low scores and lopsided results.
2. **CELEBRATES THE WINNERS** - Give credit where it's due, but with playful jabs
3. **HIGHLIGHTS THE DRAMA** - Focus on the biggest blowouts and the closest games
4. **BE BRUTAL BUT FUNNY** - Channel your inner roast comedian. Make it hurt, but make it entertaining
5. **USE CREATIVE LANGUAGE** - Sports metaphors, pop culture references, over-the-top descriptions

Guidelines:
- Keep it around 200-300 words
- Be mean to underperformers (they deserve it)
- Celebrate dominance
- Make specific references to the actual scores and matchups listed above
- End with a spicy prediction or call-out for next week
- NO generic corporate speak - this is for the league, make it personal and funny

Invention is the one unforgivable sin here: these are real people who will check
the numbers. Be funny about what actually happened."""

    return prompt


@router.get("/league/{league_id}/week/{week}")
async def get_weekly_recap(
    league_id: int,
    week: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    """
    Generate a hilarious, brutal weekly recap for a league

    This uses real matchup data and AI to create funny commentary
    """
    try:
        # Get league
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
                detail="League not found or access denied"
            )

        # Get weekly data based on platform
        if league.platform == PlatformType.ESPN:
            # Get ESPN credentials
            cookies = None
            if league.espn_s2_encrypted or league.espn_swid_encrypted:
                s2 = ESPNCredentialManager.decrypt_espn_s2(league.espn_s2_encrypted) if league.espn_s2_encrypted else None
                swid = ESPNCredentialManager.decrypt_espn_swid(league.espn_swid_encrypted) if league.espn_swid_encrypted else None
                if s2 or swid:
                    cookies = ESPNCookies(espn_s2=s2, swid=swid)

            weekly_data = await get_espn_weekly_data(league, week, cookies)

        elif league.platform == PlatformType.SLEEPER:
            weekly_data = await get_sleeper_weekly_data(league, week)

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported platform: {league.platform}"
            )

        # No resolvable matchups means there is nothing to write about. Prompting
        # anyway is what produced recaps about teams that do not exist.
        lines = build_recap_lines(week, weekly_data)
        if not lines:
            logger.info("No matchup data for recap", league_id=league_id, week=week)
            return {
                "recap": (
                    f"No matchup data for Week {week} yet. Once the week's games are "
                    f"on the board, the roast writes itself."
                ),
                "week": week,
                "league_name": league.name,
                "generated_at": None
            }

        # Check if LLM is available
        if not llm_service.is_available():
            return {
                "recap": "AI recap unavailable. Please configure GROQ_API_KEY to enable hilarious weekly recaps!",
                "week": week,
                "league_name": league.name,
                "generated_at": None
            }

        # Generate recap with LLM
        prompt = build_recap_prompt(league.name, week, lines)

        recap_text = llm_service.complete(
            system=(
                "You are a witty, brutally honest fantasy football analyst who writes "
                "hilarious weekly recaps. You roast bad performances and celebrate "
                "dominance. You work strictly from the matchup data you are given: you "
                "never invent teams, managers, players or scores, and you never mention "
                "an individual player, because you are never given player data."
            ),
            prompt=prompt,
            temperature=0.8,  # Higher temperature for more creative/funny responses
            # A recap runs 250-350 words, but the default model reasons first and that
            # reasoning comes out of the same budget: at 800 the recap ended mid-sentence.
            max_tokens=2000,
            purpose="weekly_recap",
        )

        logger.info(
            "Weekly recap generated",
            league_id=league_id,
            week=week,
            matchups=len(lines),
        )

        return {
            "recap": recap_text,
            "week": week,
            "league_name": league.name,
            "generated_at": "just now"
        }

    except HTTPException:
        raise
    except (ESPNError, SleeperError) as e:
        logger.error("Platform API error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch league data: {str(e)}"
        )
    except Exception as e:
        logger.error("Failed to generate weekly recap", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recap. Check logs for details."
        )


@router.get("/health")
async def recap_health():
    """Check if recap service is available"""
    return {
        "llm_available": llm_service.is_available(),
        "status": "ready" if llm_service.is_available() else "needs_api_key"
    }

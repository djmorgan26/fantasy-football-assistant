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


def build_recap_prompt(league_name: str, week: int, weekly_data: Dict[str, Any]) -> str:
    """Build a prompt for generating a hilarious, brutal weekly recap"""

    platform = weekly_data.get("platform", "Unknown")

    # Build matchup summary
    matchup_text = "MATCHUP RESULTS:\n"

    if platform == "ESPN":
        matchups = weekly_data.get("matchups", [])
        teams_dict = {team["id"]: team for team in weekly_data.get("teams", [])}

        for matchup in matchups:
            home = matchup.get("home", {})
            away = matchup.get("away")

            home_team = teams_dict.get(home.get("team_id"))
            home_name = home_team.get("name", "Unknown") if home_team else "Unknown"
            home_score = home.get("total_points", 0)

            if away:
                away_team = teams_dict.get(away.get("team_id"))
                away_name = away_team.get("name", "Unknown") if away_team else "Unknown"
                away_score = away.get("total_points", 0)

                winner = home_name if home_score > away_score else away_name
                loser = away_name if home_score > away_score else home_name
                winner_score = max(home_score, away_score)
                loser_score = min(home_score, away_score)
                margin = abs(home_score - away_score)

                matchup_text += f"- {winner} ({winner_score:.1f}) DESTROYED {loser} ({loser_score:.1f}) by {margin:.1f} points\n"

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
            if len(teams) == 2:
                team1, team2 = teams[0], teams[1]
                name1 = roster_owners.get(team1.get("roster_id"), "Unknown")
                name2 = roster_owners.get(team2.get("roster_id"), "Unknown")
                score1 = team1.get("points", 0)
                score2 = team2.get("points", 0)

                winner = name1 if score1 > score2 else name2
                loser = name2 if score1 > score2 else name1
                winner_score = max(score1, score2)
                loser_score = min(score1, score2)
                margin = abs(score1 - score2)

                matchup_text += f"- {winner} ({winner_score:.1f}) CRUSHED {loser} ({loser_score:.1f}) by {margin:.1f} points\n"

    prompt = f"""You are a brutally honest, hilarious fantasy football analyst writing the weekly recap for "{league_name}" Week {week}.

{matchup_text}

Write an entertaining 3-4 paragraph weekly recap that:

1. **ROASTS THE LOSERS** - Be creative and funny when describing bad performances. Call out low scores, terrible decisions, and embarrassing losses.
2. **CELEBRATES THE WINNERS** - Give credit where it's due, but with playful jabs
3. **HIGHLIGHTS THE DRAMA** - Focus on the biggest blowouts, closest games, and shocking upsets
4. **BE BRUTAL BUT FUNNY** - Channel your inner roast comedian. Make it hurt, but make it entertaining
5. **USE CREATIVE LANGUAGE** - Sports metaphors, pop culture references, over-the-top descriptions

Guidelines:
- Keep it around 200-300 words
- Be mean to underperformers (they deserve it)
- Celebrate dominance
- Make specific references to actual scores and matchups
- End with a spicy prediction or call-out for next week
- NO generic corporate speak - this is for the league, make it personal and funny

Write the recap in a fun, engaging style. This should be the kind of recap that makes people laugh at themselves."""

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
                League.owner_user_id == current_user.id
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

        # Check if LLM is available
        if not llm_service.is_available():
            return {
                "recap": "AI recap unavailable. Please configure GROQ_API_KEY to enable hilarious weekly recaps!",
                "week": week,
                "league_name": league.name,
                "generated_at": None
            }

        # Generate recap with LLM
        prompt = build_recap_prompt(league.name, week, weekly_data)

        response = llm_service.client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a witty, brutally honest fantasy football analyst who writes hilarious weekly recaps. You're not afraid to roast bad performances and celebrate dominance. Keep it fun and entertaining."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model=llm_service.model,
            temperature=0.8,  # Higher temperature for more creative/funny responses
            max_tokens=800
        )

        recap_text = response.choices[0].message.content

        logger.info(
            "Weekly recap generated",
            league_id=league_id,
            week=week,
            tokens=response.usage.total_tokens
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

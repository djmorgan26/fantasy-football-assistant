"""
Idempotent database seeding for MOCK_MODE.

On startup in mock mode we drop a ready-to-use demo account into the (SQLite)
database: one demo user, an ESPN-flavored league and a Sleeper-flavored league
(both owned by the demo user), and a pre-filled content/voice profile so the
Press Box and Draft Room are immediately populated. Re-running is safe; existing
rows are left alone.
"""
import structlog
from sqlalchemy import select

from app.db.database import SessionLocal
from app.core.auth import get_password_hash
from app.models.user import User
from app.models.league import League, PlatformType
from app.models.team import Team
from app.models.content_profile import LeagueContentProfile
from app.services import mock_data

logger = structlog.get_logger()


async def seed_mock_data() -> None:
    async with SessionLocal() as db:
        # ---- demo user ------------------------------------------------------
        result = await db.execute(select(User).where(User.email == mock_data.DEMO_USER_EMAIL))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email=mock_data.DEMO_USER_EMAIL,
                hashed_password=get_password_hash(mock_data.DEMO_USER_PASSWORD),
                full_name=mock_data.DEMO_USER_NAME,
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info("Seeded demo user", email=user.email)

        # ---- ESPN league + teams -------------------------------------------
        info = mock_data.espn_league_info()
        result = await db.execute(
            select(League).where(League.espn_league_id == mock_data.MOCK_ESPN_LEAGUE_ID)
        )
        espn_league = result.scalar_one_or_none()
        if not espn_league:
            espn_league = League(
                platform=PlatformType.ESPN,
                espn_league_id=mock_data.MOCK_ESPN_LEAGUE_ID,
                name=f"{info['name']} (ESPN)",
                season_year=mock_data.MOCK_SEASON,
                size=info["size"],
                scoring_type=info["scoring_type"],
                roster_settings=info["roster_settings"],
                scoring_settings=info["scoring_settings"],
                current_week=info["current_week"],
                owner_user_id=user.id,
                is_active=True,
            )
            db.add(espn_league)
            await db.commit()
            await db.refresh(espn_league)

            for t in mock_data.espn_teams():
                db.add(Team(
                    espn_team_id=t["id"],
                    league_id=espn_league.id,
                    name=t["name"],
                    location=t["location"],
                    nickname=t["nickname"],
                    abbreviation=t["abbreviation"],
                    logo_url=t["logo_url"],
                    wins=t["wins"],
                    losses=t["losses"],
                    ties=t["ties"],
                    points_for=t["points_for"],
                    points_against=t["points_against"],
                ))
            await db.commit()
            logger.info("Seeded mock ESPN league", league_id=espn_league.id)

        # ---- Sleeper league -------------------------------------------------
        result = await db.execute(
            select(League).where(League.sleeper_league_id == mock_data.MOCK_SLEEPER_LEAGUE_ID)
        )
        sleeper_league = result.scalar_one_or_none()
        if not sleeper_league:
            sleeper_league = League(
                platform=PlatformType.SLEEPER,
                sleeper_league_id=mock_data.MOCK_SLEEPER_LEAGUE_ID,
                sleeper_user_id=mock_data.MOCK_SLEEPER_USER_ID,
                name=f"{info['name']} (Sleeper)",
                season_year=mock_data.MOCK_SEASON,
                size=info["size"],
                scoring_type="ppr",
                current_week=info["current_week"],
                owner_user_id=user.id,
                is_active=True,
            )
            db.add(sleeper_league)
            await db.commit()
            await db.refresh(sleeper_league)

            # Teams, mirroring what the real Sleeper connect flow creates so
            # "Select My Team" and the team pages work in the demo.
            users = mock_data.sleeper_league_users()
            for roster in mock_data.sleeper_rosters():
                owner = next(
                    (u for u in users if u["user_id"] == roster["owner_id"]), None
                )
                team_name = (
                    (owner or {}).get("metadata", {}).get("team_name")
                    or (owner or {}).get("display_name")
                    or f"Team {roster['roster_id']}"
                )
                settings_ = roster.get("settings", {})
                db.add(Team(
                    league_id=sleeper_league.id,
                    sleeper_roster_id=roster["roster_id"],
                    sleeper_owner_id=roster["owner_id"],
                    name=team_name,
                    wins=settings_.get("wins", 0),
                    losses=settings_.get("losses", 0),
                    ties=settings_.get("ties", 0),
                    points_for=float(settings_.get("fpts", 0)),
                    points_against=float(settings_.get("fpts_against", 0)),
                ))
            await db.commit()
            logger.info("Seeded mock Sleeper league", league_id=sleeper_league.id)

        # ---- content / voice profiles for both leagues ----------------------
        for league in (espn_league, sleeper_league):
            result = await db.execute(
                select(LeagueContentProfile).where(
                    LeagueContentProfile.league_id == league.id
                )
            )
            if result.scalar_one_or_none():
                continue
            db.add(LeagueContentProfile(
                league_id=league.id,
                voice_guide=mock_data.seed_voice_guide(),
                humor_examples=mock_data.seed_humor_examples(),
                personas=mock_data.seed_personas(),
            ))
        await db.commit()
        logger.info("Mock data seeding complete")

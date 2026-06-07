"""Mock-mode seeding: must be idempotent and create both demo leagues."""
import pytest
from sqlalchemy import select, func

from app.models.user import User
from app.models.league import League
from app.models.team import Team
from app.models.content_profile import LeagueContentProfile
from app.services import mock_seed, mock_data


pytestmark = pytest.mark.integration


@pytest.fixture
def seedable_db(db_session, monkeypatch, mock_mode):
    """Point the seeder's session factory at the test database."""
    from tests.conftest import TestingSessionLocal

    monkeypatch.setattr(mock_seed, "SessionLocal", TestingSessionLocal)
    return db_session


async def _counts(db):
    users = (await db.execute(select(func.count()).select_from(User))).scalar()
    leagues = (await db.execute(select(func.count()).select_from(League))).scalar()
    teams = (await db.execute(select(func.count()).select_from(Team))).scalar()
    profiles = (
        await db.execute(select(func.count()).select_from(LeagueContentProfile))
    ).scalar()
    return users, leagues, teams, profiles


class TestSeed:
    async def test_seed_creates_demo_world(self, seedable_db):
        await mock_seed.seed_mock_data()
        users, leagues, teams, profiles = await _counts(seedable_db)
        assert users == 1
        assert leagues == 2
        # Regression: the Sleeper league used to be seeded with no teams,
        # leaving "Select My Team" empty in the demo. 10 ESPN + 10 Sleeper.
        assert teams == 20
        assert profiles == 2

        result = await seedable_db.execute(
            select(Team).join(League, Team.league_id == League.id).where(
                League.sleeper_league_id == mock_data.MOCK_SLEEPER_LEAGUE_ID
            )
        )
        sleeper_teams = result.scalars().all()
        assert len(sleeper_teams) == 10
        assert all(t.sleeper_roster_id is not None for t in sleeper_teams)

    async def test_seed_is_idempotent(self, seedable_db):
        await mock_seed.seed_mock_data()
        first = await _counts(seedable_db)
        await mock_seed.seed_mock_data()
        assert await _counts(seedable_db) == first

    async def test_demo_user_can_log_in(self, client, seedable_db):
        await mock_seed.seed_mock_data()
        resp = await client.post(
            "/api/auth/login",
            json={
                "email": mock_data.DEMO_USER_EMAIL,
                "password": mock_data.DEMO_USER_PASSWORD,
            },
        )
        assert resp.status_code == 200

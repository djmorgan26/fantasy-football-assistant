"""Yahoo Fantasy parsing and OAuth configuration guards."""
from app.services.yahoo_service import YahooService, _resource_records


def test_yahoo_requires_both_oauth_credentials(monkeypatch):
    monkeypatch.setattr("app.services.yahoo_service.settings.yahoo_client_id", "client")
    monkeypatch.setattr("app.services.yahoo_service.settings.yahoo_client_secret", "")
    assert YahooService().configured() is False


def test_yahoo_resource_records_unwrap_count_keyed_data():
    # Yahoo nests resource fields in arrays mixed with numeric count keys. The
    # parser must find actual resources without depending on those key names.
    payload = {
        "fantasy_content": {
            "users": {
                "0": {
                    "user": [
                        {"leagues": {"0": {"league": [
                            {"league_key": "nfl.l.42"}, {"name": "The League"},
                            {"season": "2026"}, {"num_teams": "12"},
                        ]}}}
                    ]
                }
            }
        }
    }
    records = _resource_records(payload, "league")
    assert records == [{"league_key": "nfl.l.42", "name": "The League", "season": "2026", "num_teams": "12"}]


# --------------------------------------------------------------------------
# Regressions. The Yahoo connect path was written against the pre-membership
# code and reintroduced two bugs that had already been fixed for ESPN and
# Sleeper, so both get a test here rather than only in test_league_membership.
# --------------------------------------------------------------------------
import pytest
from httpx import AsyncClient

from app.models.league import League, PlatformType
from app.models.league_member import LeagueMember
from app.models.user import User
from sqlalchemy import select


LEAGUE_KEY = "461.l.90210"

YAHOO_LEAGUE = {"name": "Yahoo Test League", "season": "2026", "num_teams": "2", "current_week": "1"}
YAHOO_TEAMS = [
    {"id": f"{LEAGUE_KEY}.t.1", "name": "Bein N Co.", "abbreviation": "BNC", "logo_url": None,
     "wins": 1, "losses": 0, "ties": 0, "points_for": 120.5, "points_against": 99.0},
    {"id": f"{LEAGUE_KEY}.t.2", "name": "Mind Goblins", "abbreviation": "MG", "logo_url": None,
     "wins": 0, "losses": 1, "ties": 0, "points_for": 99.0, "points_against": 120.5},
]


@pytest.fixture
def yahoo_stub(monkeypatch):
    """Stand in for Yahoo, which cannot be reached without real OAuth."""
    async def fake_league_and_teams(self, user, league_key):
        return dict(YAHOO_LEAGUE), [dict(t) for t in YAHOO_TEAMS]

    monkeypatch.setattr(
        "app.services.yahoo_service.YahooService.league_and_teams", fake_league_and_teams
    )


async def _yahoo_user(client: AsyncClient, db_session, email: str, name: str) -> dict:
    """A registered user who has already completed the Yahoo OAuth handshake."""
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "testpassword123", "full_name": name},
    )
    assert resp.status_code == 200, resp.text
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    user = (await db_session.execute(select(User).where(User.email == email))).scalar_one()
    user.yahoo_guid = f"guid-{user.id}"
    user.yahoo_refresh_token_encrypted = "stub"
    await db_session.commit()
    return headers


@pytest.mark.integration
async def test_second_manager_does_not_steal_a_yahoo_league(
    client: AsyncClient, db_session, yahoo_stub
):
    first = await _yahoo_user(client, db_session, "yahoo-one@example.com", "Manager One")
    second = await _yahoo_user(client, db_session, "yahoo-two@example.com", "Manager Two")

    a = await client.post("/api/yahoo/connect", json={"league_key": LEAGUE_KEY}, headers=first)
    assert a.status_code == 200, a.text
    league_id = a.json()["league_id"]

    b = await client.post("/api/yahoo/connect", json={"league_key": LEAGUE_KEY}, headers=second)
    assert b.status_code == 200, b.text
    # Same row, and the first manager still owns it.
    assert b.json()["league_id"] == league_id

    league = (await db_session.execute(select(League).where(League.id == league_id))).scalar_one()
    await db_session.refresh(league)
    owner_email = (await db_session.execute(
        select(User.email).where(User.id == league.owner_user_id)
    )).scalar_one()
    assert owner_email == "yahoo-one@example.com"
    assert league.platform == PlatformType.YAHOO

    # And both of them can still reach it.
    for headers in (first, second):
        assert (await client.get(f"/api/leagues/{league_id}", headers=headers)).status_code == 200


@pytest.mark.integration
async def test_connecting_yahoo_puts_you_in_the_league(
    client: AsyncClient, db_session, yahoo_stub
):
    """Without a membership row the board is unreachable for everyone but the
    owner, which is the whole point of the table."""
    first = await _yahoo_user(client, db_session, "yahoo-three@example.com", "Manager Three")
    second = await _yahoo_user(client, db_session, "yahoo-four@example.com", "Manager Four")

    resp = await client.post("/api/yahoo/connect", json={"league_key": LEAGUE_KEY}, headers=first)
    league_id = resp.json()["league_id"]
    await client.post("/api/yahoo/connect", json={"league_key": LEAGUE_KEY}, headers=second)

    members = (await db_session.execute(
        select(LeagueMember).where(LeagueMember.league_id == league_id)
    )).scalars().all()
    assert {m.role for m in members} == {"owner", "member"}
    # Each manager's own Yahoo identity lands on their membership, not on the
    # league row, which only ever holds the owner's.
    assert all(m.yahoo_guid for m in members)

    # The board is the thing membership exists for.
    body = "Yahoo league, same board, same rules. Let us see if this posts."
    posted = await client.post(
        f"/api/board/{league_id}/posts", json={"body": body}, headers=second
    )
    assert posted.status_code == 201, posted.text
    feed = await client.get(f"/api/board/{league_id}/posts", headers=first)
    assert [p["id"] for p in feed.json()] == [posted.json()["id"]]

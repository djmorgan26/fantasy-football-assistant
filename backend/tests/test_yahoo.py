"""Yahoo Fantasy parsing and OAuth configuration guards."""
import pytest
from jose import jwt
from urllib.parse import parse_qs, urlparse

from app.api.yahoo import _return_destination, _state_for
from app.core.config import settings
from app.services.yahoo_service import YahooAuthenticationError, YahooService, _resource_records


def test_yahoo_requires_both_oauth_credentials(monkeypatch):
    monkeypatch.setattr("app.services.yahoo_service.settings.yahoo_client_id", "client")
    monkeypatch.setattr("app.services.yahoo_service.settings.yahoo_client_secret", "")
    assert YahooService().configured() is False


def test_yahoo_authorization_forces_a_fresh_yahoo_login(monkeypatch):
    """The Fantasy Hub login must not dictate which Yahoo account is linked."""
    monkeypatch.setattr("app.services.yahoo_service.settings.yahoo_client_id", "client")
    monkeypatch.setattr("app.services.yahoo_service.settings.yahoo_client_secret", "secret")
    monkeypatch.setattr("app.services.yahoo_service.settings.yahoo_redirect_uri", "https://app.example/api/yahoo/callback")

    query = parse_qs(urlparse(YahooService().authorization_url("signed-state")).query)

    assert query == {
        "client_id": ["client"],
        "redirect_uri": ["https://app.example/api/yahoo/callback"],
        "response_type": ["code"],
        "state": ["signed-state"],
        "prompt": ["login"],
        # Without the fantasy read scope Yahoo hands back a token that
        # authenticates and then 401s on every league endpoint.
        "scope": ["fspt-r"],
    }


def test_yahoo_callback_returns_to_the_origin_that_started_oauth(monkeypatch):
    monkeypatch.setattr(settings, "frontend_url", "https://stale.example")
    state = _state_for(7, "https://current.example")
    payload = jwt.decode(state, settings.secret_key, algorithms=[settings.algorithm])

    assert _return_destination(payload["return_to"]) == "https://current.example/leagues/connect?platform=yahoo"
    assert _return_destination("https://current.example/not-an-origin") == "https://stale.example/leagues/connect?platform=yahoo"


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


@pytest.mark.asyncio
async def test_yahoo_roster_normalizes_player_and_lineup_data(monkeypatch):
    payload = {"fantasy_content": {"team": {"roster": {"0": {"players": {"0": {"player": [
        {"player_key": "nfl.p.1"}, {"player_id": "1"}, {"name": {"full": "A Player"}},
        {"display_position": "WR"}, {"editorial_team_abbr": "PHI"}, {"status": "IR"},
        {"selected_position": [{"coverage_type": "week"}, {"position": "IR"}]},
        {"eligible_positions": [{"position": "WR"}, {"position": "W/R/T"}]},
    ]}}}}}}}

    service = YahooService()
    async def get(_user, _path):
        return payload
    monkeypatch.setattr(service, "_get", get)

    roster = await service.team_roster(object(), "nfl.l.1.t.1", 3)

    assert roster == [{
        "player_id": "1", "full_name": "A Player", "position_id": 0, "position_name": "WR",
        "lineup_slot_id": 21, "lineup_slot_name": "IR", "is_starter": False,
        "on_injured_reserve": True, "pro_team_id": 0, "pro_team_abbr": "PHI",
        "eligible_slots": ["WR", "W/R/T"], "projected_points": 0.0, "applied_points": 0.0,
        "season_points": 0.0, "stats": {"actual": {}, "projected": {}},
        "injury_status": "INJURY_RESERVE",
    }]


@pytest.mark.asyncio
async def test_yahoo_leagues_put_the_current_season_first(monkeypatch):
    """Yahoo returns every season ever played, oldest first."""
    payload = {"fantasy_content": {"users": {"0": {"user": [{"games": {
        "0": {"game": [{"leagues": {"0": {"league": [
            {"league_key": "nfl.l.old", "name": "Old League", "season": "2019", "num_teams": "10"},
        ]}, "1": {"league": [
            {"league_key": "nfl.l.new", "name": "Current League", "season": "2026", "num_teams": "12"},
        ]}, "count": 2}}]},
    }}]}, "count": 1}}}

    service = YahooService()
    async def get(_user, _path):
        return payload
    monkeypatch.setattr(service, "_get", get)

    leagues = await service.leagues_for_user(object())

    assert [league["league_key"] for league in leagues] == ["nfl.l.new", "nfl.l.old"]


@pytest.mark.asyncio
async def test_yahoo_denial_names_the_missing_fantasy_permission(monkeypatch):
    """A 401 from Yahoo must say what to do, not just that something failed.

    Silently flattening this to "could not load this data" is what made a
    missing Fantasy Sports read scope impossible to tell apart from an
    expired token or a wrong Yahoo account.
    """
    class Response:
        status_code = 401
        text = '{"error": {"description": "Please provide valid credentials"}}'
        def json(self):
            return {"error": {"description": "Please provide valid credentials"}}

    service = YahooService()
    async def token(_user):
        return "token"
    monkeypatch.setattr(service, "access_token_for", token)

    class Client:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *_args):
            return False
        async def get(self, *_args, **_kwargs):
            return Response()
    monkeypatch.setattr("app.services.yahoo_service.httpx.AsyncClient", lambda **_kwargs: Client())

    with pytest.raises(YahooAuthenticationError) as raised:
        await service.leagues_for_user(object())

    assert "Fantasy Sports read permission" in str(raised.value)
    assert "Please provide valid credentials" in str(raised.value)

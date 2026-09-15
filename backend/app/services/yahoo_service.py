"""Yahoo Fantasy OAuth and read-only league synchronization.

Yahoo's Fantasy API is private by design. This module keeps its OAuth tokens
server-side, refreshes them before use, and converts Yahoo's count-keyed JSON
responses into the app's small common league/team shape.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.utils.encryption import decrypt_data, encrypt_data

AUTHORIZE_URL = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
FANTASY_URL = "https://fantasysports.yahooapis.com/fantasy/v2"


class YahooError(Exception):
    pass


class YahooConfigurationError(YahooError):
    pass


class YahooAuthenticationError(YahooError):
    pass


def _flatten(value: Any) -> Dict[str, Any]:
    """Flatten Yahoo's ``[{field: value}, ...]`` resource representation."""
    if isinstance(value, dict):
        return value
    out: Dict[str, Any] = {}
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                out.update(item)
    return out


def _resource_records(data: Any, resource: str) -> List[Dict[str, Any]]:
    """Find and normalize resources regardless of Yahoo's numeric wrappers."""
    records: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        value = data.get(resource)
        if isinstance(value, (list, dict)):
            record = _flatten(value)
            if record:
                records.append(record)
        for child in data.values():
            records.extend(_resource_records(child, resource))
    elif isinstance(data, list):
        for child in data:
            records.extend(_resource_records(child, resource))
    return records


def _value(value: Any, default: Any = None) -> Any:
    """Extract Yahoo's scalar values from its list-or-dict resource shape."""
    if isinstance(value, (list, dict)):
        value = _flatten(value)
        if isinstance(value, dict):
            return value.get("value", default)
    return value if value is not None else default


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(_value(value, default) or default)
    except (TypeError, ValueError):
        return default


def _player_name(record: Dict[str, Any]) -> str:
    name = _flatten(record.get("name"))
    return str(name.get("full") or record.get("name") or record.get("player_key") or "Unknown player")


def _injury_status(record: Dict[str, Any]) -> str | None:
    raw = str(_value(record.get("status"), "") or "").upper()
    if not raw:
        return None
    if raw in {"IR", "INJURED_RESERVE", "PUP"}:
        return "INJURY_RESERVE"
    if raw in {"O", "OUT"}:
        return "OUT"
    if raw in {"D", "DOUBTFUL"}:
        return "DOUBTFUL"
    if raw in {"Q", "QUESTIONABLE", "GTD"}:
        return "QUESTIONABLE"
    return raw


def _values_for_key(data: Any, key: str) -> List[Any]:
    """Find scalar values in Yahoo's recursively wrapped collections."""
    found: List[Any] = []
    if isinstance(data, dict):
        for name, value in data.items():
            if name == key:
                found.append(_value(value))
            found.extend(_values_for_key(value, key))
    elif isinstance(data, list):
        for item in data:
            found.extend(_values_for_key(item, key))
    return found


class YahooService:
    def configured(self) -> bool:
        return bool(settings.yahoo_client_id and settings.yahoo_client_secret)

    def authorization_url(self, state: str) -> str:
        if not self.configured():
            raise YahooConfigurationError("Yahoo Fantasy is not configured on this deployment")
        # Fantasy Hub and Yahoo authentication are deliberately separate. A
        # user may sign in here with Gmail, then connect leagues owned by a
        # different Yahoo account. Without this prompt, Yahoo can silently
        # reuse whichever account is active in the browser session.
        params = {
            "client_id": settings.yahoo_client_id,
            "redirect_uri": settings.yahoo_redirect_uri,
            "response_type": "code",
            "state": state,
            "prompt": "login",
        }
        return f"{AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        return await self._token_request({"grant_type": "authorization_code", "code": code, "redirect_uri": settings.yahoo_redirect_uri})

    async def _token_request(self, payload: Dict[str, str]) -> Dict[str, Any]:
        if not self.configured():
            raise YahooConfigurationError("Yahoo Fantasy is not configured on this deployment")
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    TOKEN_URL,
                    data=payload,
                    auth=(settings.yahoo_client_id, settings.yahoo_client_secret),
                    headers={"Accept": "application/json"},
                )
        except httpx.HTTPError as exc:
            raise YahooAuthenticationError("Could not reach Yahoo authorization") from exc
        if response.status_code >= 400:
            raise YahooAuthenticationError("Yahoo rejected the authorization request")
        try:
            data = response.json()
        except ValueError as exc:
            raise YahooAuthenticationError("Yahoo returned an invalid authorization response") from exc
        if not data.get("access_token"):
            raise YahooAuthenticationError("Yahoo did not return an access token")
        return data

    def store_tokens(self, user: Any, tokens: Dict[str, Any]) -> None:
        user.yahoo_access_token_encrypted = encrypt_data(tokens["access_token"])
        if tokens.get("refresh_token"):
            user.yahoo_refresh_token_encrypted = encrypt_data(tokens["refresh_token"])
        user.yahoo_guid = tokens.get("xoauth_yahoo_guid") or user.yahoo_guid
        user.yahoo_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(tokens.get("expires_in") or 3600))

    async def access_token_for(self, user: Any) -> str:
        expiry = user.yahoo_token_expires_at
        if expiry and expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        token = decrypt_data(user.yahoo_access_token_encrypted)
        if token and expiry and expiry > datetime.now(timezone.utc) + timedelta(minutes=2):
            return token
        refresh = decrypt_data(user.yahoo_refresh_token_encrypted)
        if not refresh:
            raise YahooAuthenticationError("Reconnect Yahoo to continue syncing this league")
        tokens = await self._token_request({"grant_type": "refresh_token", "refresh_token": refresh, "redirect_uri": settings.yahoo_redirect_uri})
        self.store_tokens(user, tokens)
        return decrypt_data(user.yahoo_access_token_encrypted) or ""

    async def _get(self, user: Any, path: str) -> Dict[str, Any]:
        token = await self.access_token_for(user)
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(f"{FANTASY_URL}/{path}", params={"format": "json"}, headers={"Authorization": f"Bearer {token}"})
        except httpx.HTTPError as exc:
            raise YahooError("Could not reach Yahoo Fantasy") from exc
        if response.status_code == 401:
            raise YahooAuthenticationError("Yahoo authorization expired; reconnect Yahoo and try again")
        if response.status_code >= 400:
            raise YahooError("Yahoo Fantasy could not load this data")
        try:
            return response.json()
        except ValueError as exc:
            raise YahooError("Yahoo Fantasy returned invalid data") from exc

    async def leagues_for_user(self, user: Any) -> List[Dict[str, Any]]:
        raw = await self._get(user, "users;use_login=1/games;game_codes=nfl/leagues")
        seen, leagues = set(), []
        for record in _resource_records(raw, "league"):
            key = record.get("league_key")
            if key and key not in seen:
                seen.add(key)
                leagues.append({"league_key": key, "name": record.get("name") or key, "season": int(record.get("season") or 0), "num_teams": int(record.get("num_teams") or 0)})
        return leagues

    async def league_and_teams(self, user: Any, league_key: str) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        metadata = await self._get(user, f"league/{league_key}")
        standings = await self._get(user, f"league/{league_key}/standings")
        leagues = _resource_records(metadata, "league")
        if not leagues:
            raise YahooError("Yahoo did not return that league")
        league = leagues[0]
        teams = []
        seen = set()
        for record in _resource_records(standings, "team"):
            team_key = record.get("team_key")
            if not team_key or team_key in seen:
                continue
            seen.add(team_key)
            standings = _flatten(record.get("team_standings"))
            outcome = _flatten(standings.get("outcome_totals"))
            points = _flatten(standings.get("points_for"))
            teams.append({
                "id": team_key, "name": record.get("name") or team_key,
                "abbreviation": record.get("team_key", "")[-10:], "logo_url": _flatten(_flatten(record.get("team_logos")).get("team_logo")).get("url"),
                "wins": int(outcome.get("wins") or 0), "losses": int(outcome.get("losses") or 0), "ties": int(outcome.get("ties") or 0),
                "points_for": float(points.get("value") or 0), "points_against": 0.0,
            })
        return league, teams

    async def team_roster(self, user: Any, team_key: str, week: int | None = None) -> List[Dict[str, Any]]:
        """Return Yahoo players in the roster shape consumed by the UI."""
        suffix = f";week={week}" if week else ""
        raw = await self._get(user, f"team/{team_key}/roster{suffix}")
        roster: List[Dict[str, Any]] = []
        for record in _resource_records(raw, "player"):
            selected = _flatten(record.get("selected_position"))
            slot = str(selected.get("position") or "BN")
            on_ir = slot.upper() in {"IR", "IR+", "IL", "NA", "PUP"}
            is_starter = slot.upper() not in {"BN", "BENCH", "IR", "IR+", "IL", "NA", "PUP"}
            positions = [str(value) for value in _values_for_key(record.get("eligible_positions"), "position") if value]
            roster.append({
                # Yahoo's player id is provider-specific, just as Sleeper's is.
                "player_id": str(record.get("player_id") or record.get("player_key") or ""),
                "full_name": _player_name(record),
                "position_id": 0,
                "position_name": str(_value(record.get("display_position"), "UNKNOWN")),
                "lineup_slot_id": 21 if on_ir else (0 if is_starter else 20),
                "lineup_slot_name": "IR" if on_ir else (slot if is_starter else "BENCH"),
                "is_starter": is_starter and not on_ir,
                "on_injured_reserve": on_ir,
                "pro_team_id": 0,
                "pro_team_abbr": str(_value(record.get("editorial_team_abbr"), "")),
                "eligible_slots": positions,
                "projected_points": 0.0,
                "applied_points": 0.0,
                "season_points": 0.0,
                "stats": {"actual": {}, "projected": {}},
                "injury_status": _injury_status(record),
            })
        return roster

    async def matchups(self, user: Any, league_key: str, week: int) -> List[Dict[str, Any]]:
        """Normalize Yahoo's scoreboard pairings to the shared matchup shape."""
        raw = await self._get(user, f"league/{league_key}/scoreboard;week={week}")
        normalized: List[Dict[str, Any]] = []
        for index, record in enumerate(_resource_records(raw, "matchup"), start=1):
            teams = _resource_records(record.get("teams"), "team")
            if not teams:
                continue
            def team_key(row: Dict[str, Any]) -> str | None:
                return row.get("team_key")
            def score(row: Dict[str, Any]) -> float:
                return _number(_flatten(row.get("team_points")).get("total"))
            home, away = teams[0], teams[1] if len(teams) > 1 else None
            home_score, away_score = score(home), score(away) if away else 0.0
            winner = "UNDECIDED" if not away else ("HOME" if home_score > away_score else "AWAY" if away_score > home_score else "TIE")
            normalized.append({
                "matchup_id": index,
                "week": int(_number(record.get("week"), week)),
                "home_team_id": team_key(home), "away_team_id": team_key(away) if away else None,
                "home_score": home_score, "away_score": away_score,
                "home_projected_score": None, "away_projected_score": None,
                "is_playoff": str(_value(record.get("is_playoffs"), "0")) == "1",
                "winner": winner,
            })
        return normalized

    async def waiver_budgets(self, user: Any, league_key: str) -> List[Dict[str, Any]]:
        """Fetch the live Yahoo FAAB balance for every team in a league."""
        settings_raw, teams_raw = await self._get(user, f"league/{league_key}/settings"), await self._get(user, f"league/{league_key}/teams")
        league_records = _resource_records(settings_raw, "league")
        league = league_records[0] if league_records else {}
        total = _number(league.get("faab_budget"), 100.0)
        budgets: List[Dict[str, Any]] = []
        for team in _resource_records(teams_raw, "team"):
            key = team.get("team_key")
            if not key:
                continue
            current = _number(team.get("faab_balance"), total)
            budgets.append({"team_id": key, "total_budget": total, "current_budget": current, "spent_budget": max(total - current, 0.0)})
        return budgets

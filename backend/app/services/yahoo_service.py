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


class YahooService:
    def configured(self) -> bool:
        return bool(settings.yahoo_client_id and settings.yahoo_client_secret)

    def authorization_url(self, state: str) -> str:
        if not self.configured():
            raise YahooConfigurationError("Yahoo Fantasy is not configured on this deployment")
        return f"{AUTHORIZE_URL}?{urlencode({'client_id': settings.yahoo_client_id, 'redirect_uri': settings.yahoo_redirect_uri, 'response_type': 'code', 'state': state})}"

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

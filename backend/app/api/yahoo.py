"""Authenticated Yahoo Fantasy connection endpoints."""
from datetime import datetime, timedelta, timezone
import secrets
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.core.config import settings
from app.db.database import get_database
from app.models.league import League, PlatformType
from app.models.team import Team
from app.models.user import User
from app.schemas.league import YahooConnectRequest, YahooLeagueSummary
from app.services.league_access import ensure_member
from app.services.yahoo_service import YahooAuthenticationError, YahooConfigurationError, YahooError, YahooService

router = APIRouter(prefix="/yahoo", tags=["yahoo"])


class AuthorizationResponse(BaseModel):
    authorization_url: str


class YahooConnectionResponse(BaseModel):
    success: bool
    message: str
    league_id: int | None = None


def _state_for(user_id: int) -> str:
    return jwt.encode(
        {"sub": str(user_id), "purpose": "yahoo_oauth", "nonce": secrets.token_urlsafe(18), "exp": datetime.now(timezone.utc) + timedelta(minutes=10)},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


@router.get("/status")
async def yahoo_status(current_user: User = Depends(get_current_active_user)):
    """Expose availability without ever exposing OAuth credentials or tokens."""
    return {"configured": YahooService().configured(), "connected": bool(current_user.yahoo_refresh_token_encrypted)}


@router.post("/authorize", response_model=AuthorizationResponse)
async def yahoo_authorize(current_user: User = Depends(get_current_active_user)):
    try:
        return AuthorizationResponse(authorization_url=YahooService().authorization_url(_state_for(current_user.id)))
    except YahooConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/callback", include_in_schema=False)
async def yahoo_callback(
    code: str | None = Query(default=None), state: str | None = Query(default=None),
    error: str | None = Query(default=None), db: AsyncSession = Depends(get_database),
):
    destination = f"{settings.frontend_url.rstrip('/')}/leagues/connect?platform=yahoo"
    if error or not code or not state:
        return RedirectResponse(f"{destination}&yahoo=cancelled", status_code=303)
    try:
        payload = jwt.decode(state, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("purpose") != "yahoo_oauth" or not payload.get("sub"):
            raise JWTError("invalid state")
        user = await db.get(User, int(payload["sub"]))
        if not user or not user.is_active:
            raise JWTError("user unavailable")
        service = YahooService()
        service.store_tokens(user, await service.exchange_code(code))
        await db.commit()
    except (JWTError, ValueError, YahooError):
        await db.rollback()
        return RedirectResponse(f"{destination}&yahoo=failed", status_code=303)
    return RedirectResponse(f"{destination}&yahoo=connected", status_code=303)


@router.get("/leagues", response_model=List[YahooLeagueSummary])
async def yahoo_leagues(current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_database)):
    try:
        leagues = await YahooService().leagues_for_user(current_user)
        await db.commit()  # token refresh may have updated the credential
        return leagues
    except YahooAuthenticationError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except YahooError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/connect", response_model=YahooConnectionResponse)
async def connect_yahoo_league(
    request: YahooConnectRequest, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_database),
):
    try:
        service = YahooService()
        data, teams = await service.league_and_teams(current_user, request.league_key)
        result = await db.execute(select(League).where(League.yahoo_league_key == request.league_key))
        league = result.scalar_one_or_none()
        if league is None:
            league = League(
                platform=PlatformType.YAHOO, yahoo_league_key=request.league_key, name=data.get("name") or request.league_key,
                season_year=int(data.get("season") or datetime.now().year), size=int(data.get("num_teams") or len(teams)),
                scoring_type="standard", roster_settings={}, scoring_settings={}, current_week=int(data.get("current_week") or 1),
                yahoo_user_guid=current_user.yahoo_guid, owner_user_id=current_user.id, is_active=True,
            )
            db.add(league)
            await db.flush()
        else:
            league.platform, league.is_active = PlatformType.YAHOO, True
            # Ownership is not up for grabs. See the same note in api/leagues.py:
            # reassigning it here is what locked the first manager out of their
            # own league on ESPN, and a Yahoo league is shared the same way.
            if league.owner_user_id is None:
                league.owner_user_id = current_user.id
            league.name, league.size = data.get("name") or league.name, int(data.get("num_teams") or len(teams) or league.size)
            league.season_year = int(data.get("season") or league.season_year)
            # Likewise the Yahoo account on the row: it is the owner's, and
            # every other manager's lands on their membership below.
            if league.owner_user_id == current_user.id or not league.yahoo_user_guid:
                league.yahoo_user_guid = current_user.yahoo_guid

        existing = {team.yahoo_team_key: team for team in (await db.execute(select(Team).where(Team.league_id == league.id))).scalars()}
        for team_data in teams:
            team = existing.get(team_data["id"])
            if team is None:
                team = Team(league_id=league.id, yahoo_team_key=team_data["id"], name=team_data["name"])
                db.add(team)
            team.name, team.abbreviation, team.logo_url = team_data["name"], team_data["abbreviation"], team_data["logo_url"]
            team.wins, team.losses, team.ties = team_data["wins"], team_data["losses"], team_data["ties"]
            team.points_for, team.points_against = team_data["points_for"], team_data["points_against"]
        league.last_synced = datetime.now(timezone.utc)

        # Whoever connected it belongs in it, first manager or fifth. Without
        # this a Yahoo league would be the one platform whose members cannot
        # reach the board, and every access check would fall back to ownership.
        membership = await ensure_member(
            db, league.id, current_user.id,
            role="owner" if league.owner_user_id == current_user.id else "member",
        )
        membership.yahoo_guid = current_user.yahoo_guid
        await db.commit()
        return YahooConnectionResponse(success=True, message=f"Connected to {league.name}", league_id=league.id)
    except YahooAuthenticationError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except YahooError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

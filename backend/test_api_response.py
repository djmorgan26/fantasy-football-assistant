#!/usr/bin/env python3

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import engine
from app.models.league import League
from app.models.team import Team
from app.services.espn_service import ESPNService, ESPNCookies
from app.utils.encryption import ESPNCredentialManager
from app.schemas.matchup import MatchupWithTeams
from datetime import datetime, timezone

async def test_api_response():
    """Test what the API endpoint would return"""
    print("=== Testing API Response Format ===")
    
    league_id = 1
    
    try:
        async with AsyncSession(engine) as db:
            # Get the league
            result = await db.execute(
                select(League).where(League.id == league_id)
            )
            league = result.scalar_one_or_none()
            
            if not league:
                print(f"❌ League {league_id} not found!")
                return
            
            print(f"✅ Found league: {league.name} (ESPN ID: {league.espn_league_id})")
            
            # Get fresh matchup data from ESPN
            espn_service = ESPNService()
            cookies = None
            if league.espn_s2_encrypted or league.espn_swid_encrypted:
                cookies = ESPNCookies(
                    espn_s2=ESPNCredentialManager.decrypt_espn_s2(league.espn_s2_encrypted) if league.espn_s2_encrypted else None,
                    swid=ESPNCredentialManager.decrypt_espn_swid(league.espn_swid_encrypted) if league.espn_swid_encrypted else None
                )
            
            matchups_data = await espn_service.get_matchups(
                str(league.espn_league_id),
                1,  # Week 1
                cookies
            )
            
            print(f"✅ Got {len(matchups_data)} matchups from ESPN service")
            
            # Test creating the API response format for first matchup
            if matchups_data:
                matchup_data = matchups_data[0]
                print(f"\\nFirst matchup raw data:")
                print(f"   home_team_id: {matchup_data.get('home_team_id')}")
                print(f"   away_team_id: {matchup_data.get('away_team_id')}")
                print(f"   home_score: {matchup_data.get('home_score')}")
                print(f"   away_score: {matchup_data.get('away_score')}")
                print(f"   home_projected_score: {matchup_data.get('home_projected_score')}")
                print(f"   away_projected_score: {matchup_data.get('away_projected_score')}")
                
                # Get team details like the API does
                home_team = None
                away_team = None
                
                if matchup_data.get("home_team_id"):
                    result = await db.execute(
                        select(Team).where(
                            Team.league_id == league.id,
                            Team.espn_team_id == matchup_data["home_team_id"]
                        )
                    )
                    home_team = result.scalar_one_or_none()
                
                if matchup_data.get("away_team_id"):
                    result = await db.execute(
                        select(Team).where(
                            Team.league_id == league.id,
                            Team.espn_team_id == matchup_data["away_team_id"]
                        )
                    )
                    away_team = result.scalar_one_or_none()
                
                # Create response like the API endpoint does
                matchup_with_teams = MatchupWithTeams(
                    id=matchup_data["matchup_id"],
                    matchup_id=matchup_data["matchup_id"],
                    league_id=league.id,
                    week=matchup_data["week"],
                    home_team_id=home_team.id if home_team else None,
                    away_team_id=away_team.id if away_team else None,
                    home_score=matchup_data["home_score"],
                    away_score=matchup_data["away_score"],
                    home_projected_score=matchup_data.get("home_projected_score"),
                    away_projected_score=matchup_data.get("away_projected_score"),
                    is_playoff=matchup_data["is_playoff"],
                    winner=matchup_data["winner"],
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    home_team_name=home_team.name if home_team else None,
                    away_team_name=away_team.name if away_team else None,
                    home_team_location=home_team.location if home_team else None,
                    away_team_location=away_team.location if away_team else None,
                    home_team_nickname=home_team.nickname if home_team else None,
                    away_team_nickname=away_team.nickname if away_team else None
                )
                
                print(f"\\nMatchupWithTeams object (what API returns):")
                print(f"   home_team_name: {matchup_with_teams.home_team_name}")
                print(f"   away_team_name: {matchup_with_teams.away_team_name}")
                print(f"   home_score: {matchup_with_teams.home_score}")
                print(f"   away_score: {matchup_with_teams.away_score}")
                print(f"   home_projected_score: {matchup_with_teams.home_projected_score}")
                print(f"   away_projected_score: {matchup_with_teams.away_projected_score}")
                print(f"   is_playoff: {matchup_with_teams.is_playoff}")
                
                # Convert to dict like JSON would do
                print(f"\\nAs JSON dict (what frontend receives):")
                data_dict = matchup_with_teams.dict()
                print(f"   home_projected_score: {data_dict.get('home_projected_score')}")
                print(f"   away_projected_score: {data_dict.get('away_projected_score')}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api_response())
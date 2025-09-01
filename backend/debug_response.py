#!/usr/bin/env python3

import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import engine
from app.models.league import League
from app.models.team import Team
from app.schemas.matchup import MatchupWithTeams
from app.services.espn_service import ESPNService

async def debug_response_creation():
    """Debug the response creation step specifically"""
    print("=== Debugging Response Creation ===")
    
    try:
        # Create async session
        async with AsyncSession(engine) as db:
            # Get league
            result = await db.execute(select(League).where(League.id == 1))
            league = result.scalar_one()
            
            # Get ESPN data
            espn_service = ESPNService()
            matchups_data = await espn_service.get_matchups(str(league.espn_league_id), 1)
            
            print(f"Got {len(matchups_data)} matchups from ESPN")
            
            # Try to create response objects
            matchups_with_teams = []
            
            for i, matchup_data in enumerate(matchups_data[:1]):  # Test just first matchup
                print(f"Processing matchup {i+1}...")
                print(f"  Raw data: {matchup_data}")
                
                # Get teams
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
                
                print(f"  Home team: {home_team.name if home_team else None}")
                print(f"  Away team: {away_team.name if away_team else None}")
                
                # Try to create the Pydantic object
                print(f"  Creating MatchupWithTeams object...")
                
                matchup_with_teams = MatchupWithTeams(
                    id=0,  # New matchup, no ID yet
                    matchup_id=matchup_data["matchup_id"],
                    league_id=league.id,
                    week=matchup_data["week"],
                    home_team_id=home_team.id if home_team else None,
                    away_team_id=away_team.id if away_team else None,
                    home_score=matchup_data["home_score"],
                    away_score=matchup_data["away_score"],
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
                
                print(f"  ✅ Successfully created: {matchup_with_teams}")
                matchups_with_teams.append(matchup_with_teams)
            
            print(f"✅ Successfully created {len(matchups_with_teams)} response objects")
            return matchups_with_teams
            
    except Exception as e:
        print(f"❌ Error in response creation: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(debug_response_creation())
    if result:
        print(f"Final result: {len(result)} matchups created successfully")
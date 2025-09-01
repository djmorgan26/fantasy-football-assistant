#!/usr/bin/env python3

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import engine, get_database
from app.models.league import League
from app.models.team import Team
from app.services.espn_service import ESPNService, ESPNCookies

async def debug_matchups():
    """Debug the matchup retrieval logic step by step"""
    print("=== Debugging Matchup Retrieval ===")
    
    league_id = 1
    user_id = 1
    
    try:
        # Create async session
        async with AsyncSession(engine) as db:
            print(f"1. Testing database connection...")
            
            # Get the league and verify ownership
            print(f"2. Looking for league {league_id} owned by user {user_id}...")
            result = await db.execute(
                select(League).where(
                    League.id == league_id,
                    League.owner_user_id == user_id
                )
            )
            league = result.scalar_one_or_none()
            
            if not league:
                print(f"❌ League not found!")
                return
            
            print(f"✅ Found league: {league.name} (ESPN ID: {league.espn_league_id})")
            
            # Test ESPN service
            print(f"3. Testing ESPN API connection...")
            espn_service = ESPNService()
            
            matchups_data = await espn_service.get_matchups(
                str(league.espn_league_id),
                1  # Week 1
            )
            
            print(f"✅ ESPN API returned {len(matchups_data)} matchups")
            if matchups_data:
                print(f"   Sample matchup: {matchups_data[0]}")
            
            # Test team lookup
            print(f"4. Testing team lookups...")
            
            for i, matchup_data in enumerate(matchups_data[:2]):  # Test first 2 matchups
                print(f"   Matchup {i+1}: Home team {matchup_data.get('home_team_id')} vs Away team {matchup_data.get('away_team_id')}")
                
                # Get team details
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
                    print(f"     Home team: {home_team.name if home_team else 'Not found'}")
                
                if matchup_data.get("away_team_id"):
                    result = await db.execute(
                        select(Team).where(
                            Team.league_id == league.id,
                            Team.espn_team_id == matchup_data["away_team_id"]
                        )
                    )
                    away_team = result.scalar_one_or_none()
                    print(f"     Away team: {away_team.name if away_team else 'Not found'}")
            
            print("✅ All steps completed successfully!")
            
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_matchups())
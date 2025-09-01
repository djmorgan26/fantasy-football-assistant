#!/usr/bin/env python3

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import engine
from app.models.league import League
from app.models.team import Team

async def debug_teams():
    """Debug all teams to find user's team"""
    print("=== Debugging All Teams ===")
    
    league_id = 1
    
    try:
        async with AsyncSession(engine) as db:
            # Get all teams
            teams_result = await db.execute(
                select(Team).where(Team.league_id == league_id)
            )
            teams = teams_result.scalars().all()
            
            print(f"Found {len(teams)} teams in league {league_id}:")
            
            for team in teams:
                print(f"  Team ID: {team.id}")
                print(f"  ESPN Team ID: {team.espn_team_id}")
                print(f"  Name: {team.name}")
                print(f"  Location: {team.location}")
                print(f"  Nickname: {team.nickname}")
                print(f"  Owner User ID: {team.owner_user_id}")
                print("  ---")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_teams())
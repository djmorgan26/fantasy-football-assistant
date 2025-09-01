#!/usr/bin/env python3

import asyncio
import sqlite3
import sys
import os

# Add the parent directory to sys.path so we can import app modules
sys.path.append(os.path.dirname(__file__))

from app.services.espn_service import ESPNService

async def test_sync_simulation():
    """Simulate the sync process to test if team names will be updated correctly"""
    
    print("=== Fantasy Football Assistant Sync Simulation ===\n")
    
    # Database connection
    db_path = "fantasy_football.db"
    
    print(f"1. Checking current team data in database ({db_path})...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, espn_team_id, name, abbreviation FROM teams WHERE espn_team_id = 9")
    current_team = cursor.fetchone()
    
    if current_team:
        print(f"   Current Team 9: id={current_team[0]}, name='{current_team[2]}', abbrev='{current_team[3]}'")
    else:
        print("   Team 9 not found in database!")
        conn.close()
        return
    
    print("\n2. Fetching fresh data from ESPN API...")
    
    try:
        espn_service = ESPNService()
        league_id = "1725275280"
        
        # Get teams data (same as sync would do)
        teams_data = await espn_service.get_teams(league_id, None)
        
        # Find team 9
        team_9_data = None
        for team in teams_data:
            if team["id"] == 9:
                team_9_data = team
                break
        
        if team_9_data:
            print(f"   ESPN Team 9: id={team_9_data['id']}, name='{team_9_data['name']}', abbrev='{team_9_data['abbreviation']}'")
            
            # Simulate what the sync would do
            print("\n3. Simulating sync update...")
            print(f"   Would update: name '{current_team[2]}' → '{team_9_data['name']}'")
            
            if current_team[2] != team_9_data['name']:
                print("   ✅ Update needed - team name would be changed!")
                
                # Actually perform the update to test it works
                print("\n4. Performing actual database update...")
                cursor.execute(
                    "UPDATE teams SET name = ? WHERE espn_team_id = 9",
                    (team_9_data['name'],)
                )
                conn.commit()
                
                # Verify the update
                cursor.execute("SELECT name FROM teams WHERE espn_team_id = 9")
                updated_name = cursor.fetchone()[0]
                print(f"   ✅ Database updated! New name: '{updated_name}'")
                
            else:
                print("   ℹ️  No update needed - names already match")
        else:
            print("   ❌ Team 9 not found in ESPN data!")
            
    except Exception as e:
        print(f"   ❌ Error fetching ESPN data: {e}")
    
    conn.close()
    print("\n=== Sync Simulation Complete ===")

if __name__ == "__main__":
    asyncio.run(test_sync_simulation())
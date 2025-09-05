#!/usr/bin/env python3

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import engine
from app.models.league import League
from app.services.espn_service import ESPNService, ESPNCookies
from app.utils.encryption import ESPNCredentialManager

async def test_projections():
    """Test getting projected scores for teams"""
    print("=== Testing Projected Scores ===")
    
    league_id = 1
    
    try:
        async with AsyncSession(engine) as db:
            # Get league
            result = await db.execute(select(League).where(League.id == league_id))
            league = result.scalar_one_or_none()
            
            if not league:
                print(f"❌ League {league_id} not found!")
                return
            
            print(f"✅ Found league: {league.name} (ESPN ID: {league.espn_league_id})")
            
            # Set up ESPN service
            espn_service = ESPNService()
            
            # Get ESPN credentials
            cookies = None
            if league.espn_s2_encrypted or league.espn_swid_encrypted:
                s2 = ESPNCredentialManager.decrypt_espn_s2(league.espn_s2_encrypted) if league.espn_s2_encrypted else None
                swid = ESPNCredentialManager.decrypt_espn_swid(league.espn_swid_encrypted) if league.espn_swid_encrypted else None
                if s2 or swid:
                    cookies = ESPNCookies(espn_s2=s2, swid=swid)
                    print(f"✅ Using ESPN credentials")
                else:
                    print("⚠️  No ESPN credentials found")
            else:
                print("⚠️  No encrypted ESPN credentials in database")
            
            # First, let's see what teams are available
            print(f"🔍 Getting team data to see available teams...")
            try:
                teams = await espn_service.get_teams(str(league.espn_league_id), cookies)
                print(f"✅ Found {len(teams)} teams")
                for i, team in enumerate(teams[:3]):
                    print(f"   Team {i+1}: ID={team.get('id')}, ESPN_ID={team.get('espn_team_id', team.get('teamId'))}, Name={team.get('name')}")
                
                if not teams:
                    print("❌ No teams found!")
                    return
                
                # Use the first team's ID for testing - the 'id' field from get_teams is the ESPN team ID
                first_team = teams[0] 
                test_team_espn_id = first_team.get('id')  # This is the ESPN team ID from the API
                if not test_team_espn_id:
                    print("❌ No ESPN team ID found!")
                    return
                
                print(f"   Using team: {first_team.get('name')} (ESPN ID: {test_team_espn_id})")
                
                print(f"\\n🔍 Testing team roster for team ESPN ID {test_team_espn_id}...")
                roster_data = await espn_service.get_team_roster(
                    str(league.espn_league_id), 
                    test_team_espn_id, 
                    1,  # Week 1
                    cookies
                )
                
                print(f"✅ Got roster data for team {test_team_espn_id}")
                players = roster_data.get("players", [])
                print(f"   Found {len(players)} players")
                
                if len(players) == 0:
                    print("   Full roster response keys:", list(roster_data.keys()))
                    print("   Let's check direct API call...")
                    # Direct API call to see what's available
                    params = {"view": "mRoster", "scoringPeriodId": 1}
                    raw_data = await espn_service._make_request(f"{league.espn_league_id}", cookies, params)
                    print("   Raw API keys:", list(raw_data.keys()))
                    teams_data = raw_data.get("teams", [])
                    print(f"   Raw teams found: {len(teams_data)}")
                    if teams_data:
                        first_raw_team = teams_data[0]
                        print(f"   First raw team keys: {list(first_raw_team.keys())}")
                        roster = first_raw_team.get("roster", {})
                        if roster:
                            print(f"   Raw roster keys: {list(roster.keys())}")
                            entries = roster.get("entries", [])
                            print(f"   Raw roster entries: {len(entries)}")
                            if entries:
                                first_entry = entries[0]
                                print(f"   First entry keys: {list(first_entry.keys())}")
                    return
                
                total_projected = 0.0
                starters_count = 0
                
                for i, player in enumerate(players[:5]):  # Show first 5 players
                    lineup_slot = player.get("lineup_slot_id", 0)
                    stats = player.get("stats", {})
                    projected = stats.get("projected", {})
                    projected_points = projected.get("0", 0.0)
                    
                    is_starter = lineup_slot != 20 and lineup_slot != 21
                    if is_starter:
                        total_projected += projected_points
                        starters_count += 1
                    
                    print(f"   Player {i+1}: {player.get('full_name', 'Unknown')} - Slot: {lineup_slot} - Projected: {projected_points:.1f} - {'Starter' if is_starter else 'Bench/IR'}")
                
                print(f"\\n   Total projected (from {starters_count} starters): {total_projected:.1f}")
                
                # Test the helper method
                team_data = {"teamId": test_team_espn_id}
                calculated_projection = await espn_service._calculate_team_projected_score(
                    team_data, str(league.espn_league_id), 1, cookies
                )
                result_str = f"{calculated_projection:.1f}" if calculated_projection else "None"
                print(f"   Helper method result: {result_str}")
                
            except Exception as e:
                print(f"❌ Error testing projections: {e}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_projections())
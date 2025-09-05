#!/usr/bin/env python3

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import engine
from app.models.league import League
from app.services.espn_service import ESPNService, ESPNCookies

async def debug_roster_parsing():
    """Debug the roster parsing logic"""
    print("=== Debugging Roster Parsing ===")
    
    league_id = 1
    
    try:
        async with AsyncSession(engine) as db:
            result = await db.execute(select(League).where(League.id == league_id))
            league = result.scalar_one_or_none()
            
            if not league:
                print(f"❌ League {league_id} not found!")
                return
            
            print(f"✅ Found league: {league.name} (ESPN ID: {league.espn_league_id})")
            
            espn_service = ESPNService()
            cookies = None
            
            # Test with team ID 1
            test_team_id = 1
            print(f"🔍 Testing roster parsing for team {test_team_id}...")
            
            # Direct API call
            params = {"view": "mRoster", "scoringPeriodId": 1}
            raw_data = await espn_service._make_request(f"{league.espn_league_id}", cookies, params)
            
            print(f"Raw API response keys: {list(raw_data.keys())}")
            teams = raw_data.get("teams", [])
            print(f"Raw teams count: {len(teams)}")
            
            # Find team 1
            target_team = None
            for team in teams:
                if team.get("id") == test_team_id:
                    target_team = team
                    break
            
            if not target_team:
                print(f"❌ Team {test_team_id} not found in raw data!")
                return
            
            print(f"✅ Found target team in raw data")
            print(f"   Team keys: {list(target_team.keys())}")
            
            roster_data = target_team.get("roster", {})
            print(f"   Roster keys: {list(roster_data.keys())}")
            
            entries = roster_data.get("entries", [])
            print(f"   Roster entries: {len(entries)}")
            
            if entries:
                first_entry = entries[0]
                print(f"   First entry keys: {list(first_entry.keys())}")
                
                player_pool_entry = first_entry.get("playerPoolEntry", {})
                print(f"   PlayerPoolEntry keys: {list(player_pool_entry.keys())}")
                
                player = player_pool_entry.get("player", {})
                print(f"   Player keys: {list(player.keys())}")
                print(f"   Player name: {player.get('fullName', 'Unknown')}")
                print(f"   Position ID: {player.get('defaultPositionId')}")
                print(f"   Lineup slot: {first_entry.get('lineupSlotId')}")
                
                # Check stats
                stats = player.get("stats", [])
                print(f"   Player stats entries: {len(stats)}")
                
                if stats:
                    for i, stat in enumerate(stats):
                        print(f"     Stat {i}: statSourceId={stat.get('statSourceId')}, appliedTotal={stat.get('appliedTotal', 0)}")
            
            # Now test our method
            print(f"\\n🔍 Testing get_team_roster method...")
            try:
                result = await espn_service.get_team_roster(
                    str(league.espn_league_id), 
                    test_team_id, 
                    1, 
                    cookies
                )
                print(f"✅ Method result keys: {list(result.keys())}")
                roster = result.get("roster", [])
                print(f"   Roster players: {len(roster)}")
                
                if roster:
                    first_player = roster[0]
                    print(f"   First player: {first_player.get('full_name')} - Slot: {first_player.get('lineup_slot_id')}")
                    print(f"   First player stats: {first_player.get('stats', {})}")
                    
                    # Test projected points calculation
                    print(f"\\n🔍 Testing projected points calculation...")
                    total_projected = 0.0
                    starters_count = 0
                    
                    for player in roster:
                        lineup_slot = player.get("lineup_slot_id", 0)
                        if lineup_slot != 20 and lineup_slot != 21:  # Not bench or IR
                            projected_points = espn_service._get_projected_points_for_roster_player(player)
                            total_projected += projected_points
                            starters_count += 1
                            print(f"     {player.get('full_name')} (slot {lineup_slot}): {projected_points:.1f}")
                    
                    print(f"   ✅ Total projected for {starters_count} starters: {total_projected:.1f}")
                    
                    # Test the full helper method
                    team_data = {"teamId": test_team_id}
                    calculated_projection = await espn_service._calculate_team_projected_score(
                        team_data, str(league.espn_league_id), 1, cookies
                    )
                    result_str = f"{calculated_projection:.1f}" if calculated_projection else "None"
                    print(f"   Helper method result: {result_str}")
                else:
                    print("❌ No roster players returned from method!")
            except Exception as e:
                print(f"❌ Error with method: {e}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_roster_parsing())
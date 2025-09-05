#!/usr/bin/env python3

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import engine
from app.models.league import League
from app.services.espn_service import ESPNService, ESPNCookies
from app.utils.encryption import ESPNCredentialManager

async def debug_players():
    """Debug the player search functionality"""
    print("=== Debugging Player Search ===")
    
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
                    print(f"✅ Using ESPN credentials: s2={'*' * 10 if s2 else 'None'}, swid={'*' * 10 if swid else 'None'}")
                else:
                    print("⚠️  No ESPN credentials found")
            else:
                print("⚠️  No encrypted ESPN credentials in database")
            
            # Test direct ESPN API call to see raw data  
            print(f"🔍 Season year setting: {espn_service.season_year}")
            print(f"🔍 Testing direct ESPN API call for league {league.espn_league_id}...")
            try:
                params = {"view": "players_wl"}
                raw_data = await espn_service._make_request(f"{league.espn_league_id}", cookies, params)
                
                print(f"✅ Raw ESPN API call successful")
                print(f"   Keys in response: {list(raw_data.keys())}")
                
                players_data = raw_data.get("players", [])
                print(f"   Found {len(players_data)} raw player entries")
                
                if players_data:
                    print("\nFirst player raw data:")
                    first_player = players_data[0]
                    print(f"   Keys: {list(first_player.keys())}")
                    
                    player_info = first_player.get("player", {})
                    print(f"   Player name: {player_info.get('fullName', 'Unknown')}")
                    print(f"   Player stats: {player_info.get('stats', 'None')}")
                    print(f"   onTeamId: {first_player.get('onTeamId', 'None')}")
                    
                    # Check a few more players
                    available_count = sum(1 for p in players_data if p.get("onTeamId") is None)
                    print(f"   Available players (onTeamId is None): {available_count}")
                
            except Exception as e:
                print(f"❌ Error with direct API call: {e}")
                import traceback
                traceback.print_exc()
                
            # Test get_available_players with debug
            print(f"\n🔍 Testing get_available_players for league {league.espn_league_id}...")
            try:
                # Use simpler parameters first
                params = {
                    "view": "players_wl",
                    "scoringPeriodId": 1
                }
                debug_data = await espn_service._make_request(f"{league.espn_league_id}", cookies, params)
                
                print(f"✅ Debug call with simple params - response size: {len(str(debug_data))}")
                
                debug_players = debug_data.get("players", [])
                available_debug = [p for p in debug_players if p.get("onTeamId") is None]
                print(f"   Available players in debug call: {len(available_debug)}")
                
                # Let's manually check what the filtering is doing
                method_data = await espn_service._make_request(f"{league.espn_league_id}", cookies, {
                    "view": ["players_wl", "kona_player_info"],
                    "scoringPeriodId": 1
                })
                
                print(f"\n🔍 Method data analysis:")
                method_players = method_data.get("players", [])
                print(f"   Raw method players: {len(method_players)}")
                
                available_method = 0
                with_team_id = 0
                for p in method_players:
                    if p.get("onTeamId") is None:
                        available_method += 1
                    else:
                        with_team_id += 1
                        
                print(f"   Available (onTeamId is None): {available_method}")
                print(f"   On teams (onTeamId not None): {with_team_id}")
                
                # Check first few available players from method data
                first_available = [p for p in method_players if p.get("onTeamId") is None][:3]
                for i, p in enumerate(first_available):
                    player = p.get("player", {})
                    print(f"   Player {i+1}: {player.get('fullName')} - pos_id: {player.get('defaultPositionId')} - stats: {len(player.get('stats', []))}")
                
                # Now test the method
                players = await espn_service.get_available_players(
                    str(league.espn_league_id),
                    week=1,
                    cookies=cookies
                )
                
                print(f"\n✅ Method returned {len(players)} available players")
                
                if players:
                    print("\nFirst 3 players:")
                    for i, player in enumerate(players[:3]):
                        print(f"  {i+1}. {player['full_name']} ({player['position_name']}) - {player['projected_points']:.1f} proj pts")
                        print(f"       Stats: {player.get('stats', 'None')}")
                else:
                    print("❌ No players returned from method")
                    
            except Exception as e:
                print(f"❌ Error getting available players: {e}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_players())
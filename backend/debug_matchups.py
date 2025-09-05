#!/usr/bin/env python3

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import engine
from app.models.league import League
from app.services.espn_service import ESPNService, ESPNCookies
from app.utils.encryption import ESPNCredentialManager

async def debug_matchups():
    """Debug the matchups functionality"""
    print("=== Debugging Matchups ===")
    
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
            
            # Test direct ESPN API call to see raw matchup data  
            print(f"🔍 Testing direct ESPN API call for matchups in week 1...")
            try:
                params = {"view": "mMatchup", "scoringPeriodId": 1}
                raw_data = await espn_service._make_request(f"{league.espn_league_id}", cookies, params)
                
                print(f"✅ Raw ESPN API call successful")
                print(f"   Keys in response: {list(raw_data.keys())}")
                
                schedule_data = raw_data.get("schedule", [])
                print(f"   Found {len(schedule_data)} schedule entries")
                
                if schedule_data:
                    print("\nFirst 3 matchup entries:")
                    for i, matchup in enumerate(schedule_data[:3]):
                        print(f"   Matchup {i+1}:")
                        print(f"     matchupPeriodId: {matchup.get('matchupPeriodId')}")
                        print(f"     playoffTierType: {matchup.get('playoffTierType')}")
                        print(f"     home teamId: {matchup.get('home', {}).get('teamId')}")
                        print(f"     home totalPoints: {matchup.get('home', {}).get('totalPoints', 0)}")
                        print(f"     home totalPointsLive: {matchup.get('home', {}).get('totalPointsLive', 0)}")
                        print(f"     away teamId: {matchup.get('away', {}).get('teamId')}")
                        print(f"     away totalPoints: {matchup.get('away', {}).get('totalPoints', 0)}")
                        print(f"     away totalPointsLive: {matchup.get('away', {}).get('totalPointsLive', 0)}")
                        print(f"     winner: {matchup.get('winner', 'UNDECIDED')}")
                        print(f"     All home keys: {list(matchup.get('home', {}).keys())}")
                        print(f"     All away keys: {list(matchup.get('away', {}).keys())}")
                        
                        # Look at roster data for projected points
                        home_roster = matchup.get('home', {}).get('rosterForMatchupPeriod', {})
                        if home_roster:
                            print(f"     Home roster keys: {list(home_roster.keys())}")
                            entries = home_roster.get('entries', [])
                            print(f"     Home roster entries: {len(entries)}")
                            if entries:
                                first_entry = entries[0]
                                print(f"     First home player keys: {list(first_entry.keys())}")
                                player_data = first_entry.get('playerPoolEntry', {}).get('player', {})
                                print(f"     Player stats keys: {list(player_data.get('stats', [{}])[0].keys()) if player_data.get('stats') else 'No stats'}")
                        print()
                
            except Exception as e:
                print(f"❌ Error with direct API call: {e}")
                import traceback
                traceback.print_exc()
                
            # Test get_matchups method
            print(f"🔍 Testing get_matchups method for week 1...")
            try:
                matchups = await espn_service.get_matchups(
                    str(league.espn_league_id),
                    week=1,
                    cookies=cookies
                )
                
                print(f"✅ Method returned {len(matchups)} matchups")
                
                if matchups:
                    print("\\nFirst 3 processed matchups:")
                    for i, matchup in enumerate(matchups[:3]):
                        print(f"  {i+1}. Week {matchup['week']} - Home: {matchup['home_team_id']} vs Away: {matchup['away_team_id']}")
                        print(f"       is_playoff: {matchup['is_playoff']} - Winner: {matchup['winner']}")
                        home_proj = matchup.get('home_projected_score')
                        away_proj = matchup.get('away_projected_score')
                        home_str = f"{home_proj:.1f}" if home_proj else "None"
                        away_str = f"{away_proj:.1f}" if away_proj else "None"
                        print(f"       Projected: Home {home_str} - Away {away_str}")
                        if home_proj and away_proj:
                            favorite = "Home" if home_proj > away_proj else "Away" if away_proj > home_proj else "Even"
                            print(f"       Favorite: {favorite}")
                else:
                    print("❌ No matchups returned from method")
                    
            except Exception as e:
                print(f"❌ Error getting matchups: {e}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_matchups())
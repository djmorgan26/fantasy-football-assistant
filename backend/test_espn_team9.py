#!/usr/bin/env python3

import asyncio
import httpx
import json

async def test_espn_team9():
    """Test ESPN API to get team ID 9 specifically"""
    league_id = "1725275280"
    season_year = "2025"
    
    base_url = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl"
    url = f"{base_url}/seasons/{season_year}/segments/0/leagues/{league_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; FantasyFootballAssistant/1.0)",
        "Accept": "application/json"
    }
    
    params = {"view": "mTeam"}
    
    print(f"Looking for team ID 9 in ESPN league {league_id}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                json_data = response.json()
                
                if "teams" in json_data:
                    print(f"Total teams found: {len(json_data['teams'])}")
                    
                    # Find team ID 9
                    for i, team in enumerate(json_data['teams']):
                        if team.get('id') == 9:
                            print(f"\n=== TEAM ID 9 FOUND ===")
                            print(f"Team Index: {i+1}")
                            print(f"All keys: {list(team.keys())}")
                            print(f"id: {team.get('id')}")
                            print(f"name: '{team.get('name', '')}'")
                            print(f"location: '{team.get('location', '')}'")
                            print(f"nickname: '{team.get('nickname', '')}'")
                            print(f"abbrev: '{team.get('abbrev', '')}'")
                            print(f"primaryOwner: {team.get('primaryOwner', 'N/A')}")
                            print(f"owners: {team.get('owners', [])}")
                            
                            # Look for any other name-related fields
                            name_fields = [k for k in team.keys() if 'name' in k.lower()]
                            if name_fields:
                                print(f"Name-related fields: {name_fields}")
                                for field in name_fields:
                                    print(f"  {field}: '{team.get(field, '')}'")
                            return
                    
                    print("Team ID 9 not found in the teams list")
                    print("Available team IDs:")
                    for team in json_data['teams']:
                        print(f"  ID {team.get('id')}: name='{team.get('name', '')}', abbrev='{team.get('abbrev', '')}'")
                        
                else:
                    print("No 'teams' key in response")
            else:
                print(f"Error response: {response.status_code}")
                print(response.text[:1000])
                
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_espn_team9())
#!/usr/bin/env python3

import asyncio
import httpx
import json

async def test_espn_api():
    """Test ESPN API directly to see what it returns"""
    league_id = "1725275280"
    season_year = "2025"
    
    base_url = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl"
    url = f"{base_url}/seasons/{season_year}/segments/0/leagues/{league_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; FantasyFootballAssistant/1.0)",
        "Accept": "application/json"
    }
    
    params = {"view": "mTeam"}
    
    print(f"Testing ESPN API URL: {url}")
    print(f"Parameters: {params}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            
            print(f"Status Code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print(f"Content Length: {len(response.text)}")
            
            if response.status_code == 200:
                print("Response content (first 2000 chars):")
                print(response.text[:2000])
                print("\n" + "="*50 + "\n")
                
                try:
                    json_data = response.json()
                    print(f"JSON parsed successfully. Type: {type(json_data)}")
                    if isinstance(json_data, dict):
                        print(f"Keys in response: {list(json_data.keys())}")
                        if "teams" in json_data:
                            print(f"Number of teams: {len(json_data['teams'])}")
                        else:
                            print("No 'teams' key in response")
                    else:
                        print(f"Response is not a dict, it's: {type(json_data)}")
                        print(f"Content: {json_data}")
                        
                except Exception as e:
                    print(f"Failed to parse as JSON: {e}")
                    print(f"Raw content: {response.text[:1000]}")
            else:
                print(f"Error response: {response.text[:1000]}")
                
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_espn_api())
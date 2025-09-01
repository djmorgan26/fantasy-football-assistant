#!/usr/bin/env python3

import asyncio
from app.services.espn_service import ESPNService, ESPNCookies

async def test_matchups():
    """Test getting matchup data from ESPN API"""
    league_id = "1725275280"  # Your league ID from the test file
    
    print(f"Testing matchup data for league {league_id}")
    
    try:
        service = ESPNService()
        
        # Test with no week specified (should get all matchups)
        print("Fetching all matchups...")
        matchups_all = await service.get_matchups(league_id)
        print(f"Found {len(matchups_all)} total matchups")
        
        if matchups_all:
            print("\nFirst matchup:")
            print(matchups_all[0])
        
        # Test with week 1 specifically
        print("\nFetching Week 1 matchups...")
        matchups_week1 = await service.get_matchups(league_id, week=1)
        print(f"Found {len(matchups_week1)} Week 1 matchups")
        
        if matchups_week1:
            print("\nWeek 1 matchups:")
            for i, matchup in enumerate(matchups_week1):
                print(f"  Matchup {i+1}: {matchup}")
        
    except Exception as e:
        print(f"Error testing matchups: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_matchups())
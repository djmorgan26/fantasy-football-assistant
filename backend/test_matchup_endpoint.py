#!/usr/bin/env python3

import asyncio
from datetime import datetime
from app.schemas.matchup import MatchupWithTeams

async def test_matchup_schema():
    """Test if we can create MatchupWithTeams objects"""
    try:
        # Test creating a basic matchup response
        matchup_with_teams = MatchupWithTeams(
            id=1,
            matchup_id=1,
            league_id=1,
            week=1,
            home_team_id=2,
            away_team_id=3,
            home_score=10.5,
            away_score=8.2,
            is_playoff=False,
            winner="HOME",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            home_team_name="Team A",
            away_team_name="Team B"
        )
        
        print(f"Success: Created matchup object: {matchup_with_teams}")
        return True
        
    except Exception as e:
        print(f"Error creating MatchupWithTeams: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_matchup_schema())
    print(f"Test result: {'PASSED' if success else 'FAILED'}")
# ESPN Fantasy Football API Integration

## Overview

ESPN Fantasy Football provides a RESTful API for accessing league data. While not officially documented, the API endpoints are well-understood by the fantasy football community and provide comprehensive access to league information, rosters, transactions, and player data.

## Authentication

ESPN fantasy leagues can be either public or private:

### Public Leagues
- No authentication required
- Access via league ID only
- Limited to basic league information

### Private Leagues (Recommended)
Requires ESPN session cookies:
- **espn_s2**: Primary authentication cookie
- **SWID**: Session web identifier

### Obtaining ESPN Cookies

1. **Login to ESPN Fantasy**
   - Go to https://fantasy.espn.com
   - Login to your account
   - Navigate to your fantasy league

2. **Extract Cookies (Chrome)**
   - Open Developer Tools (F12)
   - Go to Application > Storage > Cookies > https://fantasy.espn.com
   - Find and copy values for:
     - `espn_s2` (long string starting with "AEB")
     - `SWID` (format: `{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}`)

3. **Extract Cookies (Firefox)**
   - Open Developer Tools (F12)
   - Go to Storage > Cookies > https://fantasy.espn.com
   - Copy the same cookie values

## Core API Endpoints

### Base URL
```
https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{leagueId}
```

### Key Endpoints

#### League Information
```
GET /
Returns: League settings, scoring, roster requirements
```

#### Teams and Rosters
```
GET /?view=mTeam
Returns: All teams with current rosters

GET /?view=mRoster&scoringPeriodId={week}
Returns: Rosters for specific week
```

#### Player Data
```
GET /?view=players_wl&scoringPeriodId={week}
Returns: All available players with stats

GET /?view=kona_player_info
Returns: Player information and news
```

#### Matchups and Scores
```
GET /?view=mMatchup&scoringPeriodId={week}
Returns: Matchup data and scores for specific week
```

#### Transactions
```
GET /?view=mTransactions2&startDate={date}&endDate={date}
Returns: Trades, waiver claims, and add/drops
```

## Data Structures

### League Object
```json
{
  "id": 123456,
  "name": "My Fantasy League",
  "size": 12,
  "scoringPeriodId": 8,
  "currentMatchupPeriod": 8,
  "status": {
    "currentMatchupPeriod": 8,
    "isActive": true,
    "latestScoringPeriod": 8
  },
  "settings": {
    "rosterSettings": {
      "positionLimits": {
        "0": {"limit": 1},  // QB
        "2": {"limit": 2},  // RB  
        "4": {"limit": 2}   // WR
      }
    },
    "scoringSettings": {
      "scoringItems": []
    }
  }
}
```

### Team Object
```json
{
  "id": 1,
  "name": "Team Name",
  "location": "Team Location", 
  "nickname": "Team Nickname",
  "abbrev": "TN",
  "owners": [{"id": "owner-id"}],
  "roster": {
    "entries": [
      {
        "playerId": 123456,
        "lineupSlotId": 20,
        "playerPoolEntry": {
          "player": {
            "id": 123456,
            "fullName": "Player Name",
            "proTeamId": 1,
            "defaultPositionId": 2
          }
        }
      }
    ]
  }
}
```

### Player Object
```json
{
  "id": 123456,
  "fullName": "Player Name",
  "firstName": "First",
  "lastName": "Last", 
  "proTeamId": 1,
  "defaultPositionId": 2,
  "eligibleSlots": [2, 3, 23],
  "stats": [
    {
      "scoringPeriodId": 8,
      "seasonId": 2024,
      "statSourceId": 0,
      "stats": {
        "0": 15.7,  // Fantasy points
        "3": 245,   // Passing yards
        "4": 2      // Passing TDs
      }
    }
  ]
}
```

## Position IDs

ESPN uses numeric IDs for player positions:

```python
POSITION_MAP = {
    0: "QB",    # Quarterback
    1: "TQB",   # Team QB (not used in standard leagues)
    2: "RB",    # Running Back
    3: "RB/WR", # Running Back/Wide Receiver
    4: "WR",    # Wide Receiver
    5: "WR/TE", # Wide Receiver/Tight End
    6: "TE",    # Tight End
    16: "D/ST", # Defense/Special Teams
    17: "K",    # Kicker
    20: "BENCH", # Bench
    21: "IR",   # Injured Reserve
    23: "FLEX"  # Flex (RB/WR/TE)
}
```

## Lineup Slot IDs

```python
LINEUP_SLOTS = {
    0: "QB",
    2: "RB", 
    4: "WR",
    6: "TE",
    16: "D/ST",
    17: "K",
    20: "BENCH",
    21: "IR",
    23: "FLEX"
}
```

## Stat Categories

Common ESPN stat IDs for scoring:

```python
STAT_MAP = {
    0: "fantasy_points",
    3: "passing_yards", 
    4: "passing_tds",
    20: "passing_ints",
    24: "rushing_yards",
    25: "rushing_tds", 
    42: "receiving_yards",
    43: "receiving_tds",
    53: "receiving_receptions",
    72: "fumbles_lost",
    74: "made_2pt_conversions",
    129: "defensive_tds",
    133: "kick_return_tds"
}
```

## Error Handling

### Common Issues
1. **Invalid Cookies**: Results in 401 Unauthorized
   - Solution: Re-obtain cookies from browser
   - Implementation: Graceful fallback to public data

2. **Rate Limiting**: ESPN may throttle excessive requests
   - Solution: Implement exponential backoff
   - Best Practice: Cache responses for 15-30 minutes

3. **League Access**: Private leagues require proper authentication
   - Solution: Clear error messages for users
   - Fallback: Public league data when available

### Retry Strategy
```python
async def espn_request_with_retry(url, cookies=None, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = await httpx.get(url, cookies=cookies)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:  # Rate limited
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                response.raise_for_status()
        except httpx.RequestError:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(1)
    raise Exception("Max retries exceeded")
```

## Request Examples

### Get League Info
```python
import httpx

async def get_league_info(league_id, year=2024, cookies=None):
    url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{league_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; FantasyFootballAssistant/1.0)"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, cookies=cookies)
        return response.json()
```

### Get Current Week Rosters
```python
async def get_current_rosters(league_id, year=2024, week=None, cookies=None):
    base_url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{league_id}"
    
    params = {"view": "mRoster"}
    if week:
        params["scoringPeriodId"] = week
        
    async with httpx.AsyncClient() as client:
        response = await client.get(base_url, params=params, cookies=cookies)
        return response.json()
```

## Best Practices

### Performance
- **Batch Requests**: Combine multiple views in single API call using `view` parameters
- **Caching**: Cache responses for 15-30 minutes to reduce API load
- **Async Operations**: Use async/await for all ESPN API calls
- **Connection Pooling**: Reuse HTTP connections when possible

### Security
- **Cookie Encryption**: Store ESPN cookies encrypted in database
- **Environment Variables**: Never commit credentials to source control
- **Request Validation**: Validate all inputs before making ESPN API calls
- **Error Sanitization**: Don't expose internal errors to frontend

### Reliability
- **Graceful Degradation**: Continue working with cached data during API outages
- **Health Checks**: Monitor ESPN API availability
- **Fallback Data**: Use alternative data sources when ESPN is unavailable
- **User Communication**: Clear error messages when ESPN integration fails

## Data Refresh Strategy

### Real-time (WebSocket/Polling)
- Player injury updates
- Game score updates during live games
- Breaking news and alerts

### Scheduled Updates
- **Every 15 minutes**: Active game scores and player stats
- **Every hour**: Roster changes and transactions  
- **Daily at 3 AM ET**: Full league data sync
- **Weekly on Tuesday**: Waiver wire processing and rankings update

### User-Triggered Updates
- Manual refresh buttons for immediate data sync
- Pre-draft preparation and mock draft data
- Trade deadline activity monitoring
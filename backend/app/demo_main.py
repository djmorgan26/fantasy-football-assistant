from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Create FastAPI app
app = FastAPI(
    title="Fantasy Football Assistant",
    version="1.0.0",
    description="A comprehensive Fantasy Football assistant that integrates with ESPN leagues",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app_name": "Fantasy Football Assistant",
        "version": "1.0.0",
        "debug": True
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to the Fantasy Football Assistant API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# Mock API endpoints
@app.get("/api/auth/me")
async def get_current_user():
    return JSONResponse(
        status_code=401,
        content={"detail": "Authentication required - this is a demo"}
    )

@app.post("/api/auth/login")
async def login():
    return {
        "message": "Login endpoint - Phase 2 implementation",
        "note": "This is a demo. Full authentication is implemented in the complete app."
    }

@app.post("/api/auth/register")
async def register():
    return {
        "message": "Registration endpoint - Phase 2 implementation", 
        "note": "This is a demo. Full authentication is implemented in the complete app."
    }

@app.get("/api/leagues/")
async def get_leagues():
    return {
        "message": "Leagues endpoint - Phase 2 implementation",
        "demo_leagues": [
            {
                "id": 1,
                "name": "Demo Fantasy League",
                "size": 12,
                "current_week": 8,
                "scoring_type": "ppr"
            }
        ],
        "note": "This is a demo. Full ESPN integration is implemented in the complete app."
    }

@app.post("/api/leagues/connect")
async def connect_league():
    return {
        "success": True,
        "message": "ESPN league connection - Phase 2 implementation",
        "note": "This is a demo. Real ESPN API integration is implemented in the complete app."
    }

@app.get("/api/teams/league/{league_id}")
async def get_league_teams(league_id: int):
    return {
        "message": f"Teams for league {league_id} - Phase 2 implementation",
        "demo_teams": [
            {"id": 1, "name": "Demo Team 1", "wins": 6, "losses": 2},
            {"id": 2, "name": "Demo Team 2", "wins": 5, "losses": 3},
        ],
        "note": "This is a demo. Full team data is available in the complete app."
    }

@app.get("/api/players/league/{league_id}/available")
async def get_available_players(league_id: int):
    return {
        "message": f"Available players for league {league_id} - Phase 2 implementation",
        "demo_players": [
            {"id": 1, "name": "Demo Player 1", "position": "RB", "projected_points": 12.5},
            {"id": 2, "name": "Demo Player 2", "position": "WR", "projected_points": 10.2},
        ],
        "note": "This is a demo. Full player data and search is implemented in the complete app."
    }

@app.post("/api/trades/analyze")
async def analyze_trade():
    return {
        "is_valid": True,
        "fairness_score": 85.0,
        "analysis_summary": "Demo trade analysis - This is a fairly balanced trade",
        "recommendations": ["This is a demo of the trade analysis feature"],
        "note": "This is a demo. Full trade analysis with ESPN data is implemented in the complete app."
    }

if __name__ == "__main__":
    uvicorn.run("demo_main:app", host="0.0.0.0", port=8000, reload=True)
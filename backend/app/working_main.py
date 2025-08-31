import sqlite3
import bcrypt
import jwt
import asyncio
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import uvicorn
import os

# Configuration
SECRET_KEY = "demo-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
DATABASE_FILE = "fantasy_football_demo.db"

# FastAPI app
app = FastAPI(
    title="Fantasy Football Assistant",
    version="1.0.0",
    description="A comprehensive Fantasy Football assistant with working authentication",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str = None
    espn_s2: str = None
    espn_swid: str = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str = None
    is_active: bool
    has_espn_credentials: bool

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Database setup
def init_database():
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            full_name TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            espn_s2_encrypted TEXT,
            espn_swid_encrypted TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Helper functions
def get_db():
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return int(user_id)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_user_by_email(db, email: str):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    return dict(user) if user else None

def get_user_by_id(db, user_id: int):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    return dict(user) if user else None

def create_user(db, email: str, password: str, full_name: str = None, espn_s2: str = None, espn_swid: str = None):
    hashed_password = get_password_hash(password)
    cursor = db.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO users (email, hashed_password, full_name, espn_s2_encrypted, espn_swid_encrypted)
            VALUES (?, ?, ?, ?, ?)
        """, (email, hashed_password, full_name, espn_s2, espn_swid))
        
        user_id = cursor.lastrowid
        db.commit()
        
        return get_user_by_id(db, user_id)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already registered")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db = Depends(get_db)):
    user_id = verify_token(credentials.credentials)
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# API Routes
@app.on_event("startup")
async def startup_event():
    init_database()
    print("✅ Database initialized")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app_name": "Fantasy Football Assistant",
        "version": "1.0.0",
        "database": "connected",
        "auth": "enabled"
    }

@app.get("/")
async def root():
    return {
        "message": "Welcome to the Fantasy Football Assistant API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "auth": "enabled"
    }

@app.post("/api/auth/register", response_model=Token)
async def register(user_data: UserCreate, db = Depends(get_db)):
    # Check if user already exists
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = create_user(
        db=db,
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        espn_s2=user_data.espn_s2,
        espn_swid=user_data.espn_swid
    )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["id"])}, expires_delta=access_token_expires
    )
    
    user_response = UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        is_active=bool(user["is_active"]),
        has_espn_credentials=bool(user["espn_s2_encrypted"] or user["espn_swid_encrypted"])
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

@app.post("/api/auth/login", response_model=Token)
async def login(login_data: UserLogin, db = Depends(get_db)):
    user = get_user_by_email(db, login_data.email)
    if not user or not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user["is_active"]:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["id"])}, expires_delta=access_token_expires
    )
    
    user_response = UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        is_active=bool(user["is_active"]),
        has_espn_credentials=bool(user["espn_s2_encrypted"] or user["espn_swid_encrypted"])
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        is_active=bool(current_user["is_active"]),
        has_espn_credentials=bool(current_user["espn_s2_encrypted"] or current_user["espn_swid_encrypted"])
    )

# Demo endpoints for other features
@app.get("/api/leagues/")
async def get_leagues(current_user = Depends(get_current_user)):
    return {
        "message": f"Welcome {current_user['full_name'] or current_user['email']}!",
        "user_id": current_user["id"],
        "demo_leagues": [
            {
                "id": 1,
                "name": "Demo Fantasy League",
                "size": 12,
                "current_week": 8,
                "scoring_type": "ppr"
            }
        ],
        "note": "Authentication is working! This shows your protected leagues data."
    }

@app.post("/api/leagues/connect")
async def connect_league(current_user = Depends(get_current_user)):
    return {
        "success": True,
        "message": f"ESPN league connection for {current_user['email']}",
        "user_id": current_user["id"],
        "note": "Authentication verified! League connection would happen here."
    }

@app.get("/api/teams/league/{league_id}")
async def get_league_teams(league_id: int, current_user = Depends(get_current_user)):
    return {
        "message": f"Teams for league {league_id} - User: {current_user['email']}",
        "user_id": current_user["id"],
        "demo_teams": [
            {"id": 1, "name": "Demo Team 1", "wins": 6, "losses": 2},
            {"id": 2, "name": "Demo Team 2", "wins": 5, "losses": 3},
        ],
        "note": "Authentication working! Real team data would be fetched here."
    }

@app.get("/api/players/league/{league_id}/available")
async def get_available_players(league_id: int, current_user = Depends(get_current_user)):
    return {
        "players": [
            {"id": 1, "name": "Demo Player 1", "position": "RB", "projected_points": 12.5},
            {"id": 2, "name": "Demo Player 2", "position": "WR", "projected_points": 10.2},
        ],
        "total_count": 2,
        "user_id": current_user["id"],
        "note": f"Authenticated as {current_user['email']} - player search working!"
    }

@app.post("/api/trades/analyze")
async def analyze_trade(current_user = Depends(get_current_user)):
    return {
        "is_valid": True,
        "fairness_score": 85.0,
        "analysis_summary": f"Trade analysis for {current_user['full_name'] or current_user['email']}",
        "recommendations": ["Authentication is working!", "Trade analysis would happen here"],
        "user_id": current_user["id"]
    }

if __name__ == "__main__":
    uvicorn.run("working_main:app", host="0.0.0.0", port=8000, reload=True)
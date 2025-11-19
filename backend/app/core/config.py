from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str
    
    # ESPN API
    espn_api_base_url: str = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl"
    espn_season_year: int = 2025
    espn_rate_limit_requests: int = 100
    espn_rate_limit_window: int = 3600
    
    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"
    
    # Redis (optional)
    redis_url: str = "redis://localhost:6379"
    
    # Email (optional)
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    
    # Development
    debug: bool = False
    reload: bool = False
    log_level: str = "INFO"
    
    # Application
    app_name: str = "Fantasy Football Assistant"
    app_version: str = "1.0.0"

    # LLM Integration
    groq_api_key: str = ""
    llm_model: str = "llama-3.1-70b-versatile"  # Fast and capable free model

    class Config:
        env_file = ".env"


settings = Settings()
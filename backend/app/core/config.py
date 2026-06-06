from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Mock / demo mode
    # When true the whole app runs with NO external credentials and NO real API
    # calls: ESPN/Sleeper/Groq are short-circuited to realistic sample data and
    # the database is forced to a local SQLite file. Set MOCK_MODE=true in the
    # environment (see .env.mock) to launch the demo experience.
    mock_mode: bool = False

    # Database
    # Has a safe SQLite default so the app can boot in mock mode with no .env.
    # Real mode overrides this with a Postgres URL via .env.
    database_url: str = "sqlite+aiosqlite:///./fantasy_local.db"
    # File used for the database in mock mode (always SQLite, never Postgres).
    mock_database_url: str = "sqlite+aiosqlite:///./fantasy_mock.db"

    # ESPN API
    espn_api_base_url: str = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl"
    espn_season_year: int = 2025
    espn_rate_limit_requests: int = 100
    espn_rate_limit_window: int = 3600
    
    # Security
    # Default is only suitable for local mock/demo use; real mode must override
    # SECRET_KEY via .env (generate with: openssl rand -hex 32).
    secret_key: str = "dev-only-insecure-secret-change-me-for-real-mode"
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
    # NOTE: llama-3.1-70b-versatile and mixtral-8x7b-32768 were decommissioned by Groq.
    # llama-3.3-70b-versatile is the current best free balance of speed and quality.
    llm_model: str = "llama-3.3-70b-versatile"

    @property
    def effective_database_url(self) -> str:
        """The database URL actually used at runtime.

        Mock mode always uses a local SQLite file so the demo never needs (or
        touches) Postgres, regardless of what DATABASE_URL happens to be set to.
        """
        return self.mock_database_url if self.mock_mode else self.database_url

    class Config:
        env_file = ".env"
        # Ignore unknown keys (e.g. SLEEPER_API_BASE_URL, VITE_API_URL) so a
        # shared .env that also configures other tooling never breaks startup.
        extra = "ignore"


settings = Settings()
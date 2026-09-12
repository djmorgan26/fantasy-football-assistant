from datetime import date
from typing import List

from pydantic_settings import BaseSettings


def current_nfl_season() -> int:
    """The fantasy season we should target.

    From March onward the upcoming season is the one that matters (draft prep,
    offseason moves); in January/February the previous year's season is still
    wrapping up.
    """
    today = date.today()
    return today.year if today.month >= 3 else today.year - 1


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
    espn_season_year: int = 0  # 0 = derive from today's date
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

    # Trusted hosts (used in real, non-debug mode). Comma-separated; supports
    # wildcards like *.vercel.app. Override with ALLOWED_HOSTS for a custom domain.
    allowed_hosts: str = "localhost,127.0.0.1,*.vercel.app"
    
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
    # NOTE: Groq retires models regularly. llama-3.1-70b-versatile, mixtral-8x7b-32768
    # and llama-3.3-70b-versatile have all been decommissioned; a request for a retired
    # model comes back as a 404 model_not_found. Verify against GET /openai/v1/models
    # before changing this.
    llm_model: str = "openai/gpt-oss-120b"

    @property
    def effective_database_url(self) -> str:
        """The database URL actually used at runtime.

        Mock mode always uses a local SQLite file so the demo never needs (or
        touches) Postgres, regardless of what DATABASE_URL happens to be set to.
        """
        return self.mock_database_url if self.mock_mode else self.database_url

    def model_post_init(self, __context) -> None:
        if not self.espn_season_year:
            self.espn_season_year = current_nfl_season()

    class Config:
        env_file = ".env"
        # Ignore unknown keys (e.g. SLEEPER_API_BASE_URL, VITE_API_URL) so a
        # shared .env that also configures other tooling never breaks startup.
        extra = "ignore"


settings = Settings()
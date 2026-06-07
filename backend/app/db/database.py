import uuid
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool
from app.core.config import settings

# Mock mode forces SQLite; real mode uses the configured (Postgres) URL.
DATABASE_URL = settings.effective_database_url

# For SQLite, we need to handle connection args differently
if DATABASE_URL.startswith("sqlite"):
    engine = create_async_engine(
        DATABASE_URL,
        echo=settings.debug,
        future=True,
        connect_args={"check_same_thread": False}
    )
else:
    # Postgres. In serverless (Vercel) the app talks to Postgres through a
    # transaction pooler (e.g. Supabase Supavisor on port 6543), which does NOT
    # support asyncpg's server-side prepared statements: disabling the statement
    # cache alone is not enough because the prepared-statement *names* still
    # collide across pooled connections ("prepared statement ... already exists").
    # The fix is to also disable the dialect's prepared-statement cache and give
    # every prepared statement a unique name. NullPool suits serverless too: each
    # invocation gets a fresh connection that is closed after use.
    engine = create_async_engine(
        DATABASE_URL,
        echo=settings.debug,
        future=True,
        poolclass=NullPool,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
        },
    )

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


async def get_database():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_database_url():
    return DATABASE_URL
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
    # transaction pooler (e.g. Supabase Supavisor on port 6543), which does not
    # support server-side prepared statements. asyncpg uses them by default, so
    # disable its statement cache. NullPool is also the right choice for
    # serverless: each invocation gets a fresh connection that is closed after,
    # instead of holding a pool that the pooler would have to juggle.
    engine = create_async_engine(
        DATABASE_URL,
        echo=settings.debug,
        future=True,
        poolclass=NullPool,
        connect_args={"statement_cache_size": 0},
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
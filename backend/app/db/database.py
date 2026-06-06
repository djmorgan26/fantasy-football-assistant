from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
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
    engine = create_async_engine(
        DATABASE_URL,
        echo=settings.debug,
        future=True
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
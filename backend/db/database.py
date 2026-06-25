from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from core.config import settings

# Handle both SQLite and PostgreSQL
db_url = settings.DATABASE_URL

if db_url.startswith("sqlite"):
    # SQLite configuration
    sync_engine = create_engine(
        db_url.replace("+aiosqlite", ""),
        pool_pre_ping=True,
    )
    ASYNC_DATABASE_URL = db_url
    if not ASYNC_DATABASE_URL.startswith("sqlite+aiosqlite://"):
        ASYNC_DATABASE_URL = ASYNC_DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")

    async_engine = create_async_engine(
        ASYNC_DATABASE_URL,
        echo=settings.DEBUG,
    )
else:
    # PostgreSQL configuration
    sync_engine = create_engine(
        db_url.replace("+asyncpg", ""),
        pool_pre_ping=True,
    )
    ASYNC_DATABASE_URL = db_url
    if ASYNC_DATABASE_URL.startswith("postgresql://"):
        ASYNC_DATABASE_URL = ASYNC_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    elif not ASYNC_DATABASE_URL.startswith("postgresql+asyncpg://"):
        ASYNC_DATABASE_URL = ASYNC_DATABASE_URL.replace("postgres://", "postgresql+asyncpg://")

    async_engine = create_async_engine(
        ASYNC_DATABASE_URL,
        echo=settings.DEBUG,
        poolclass=NullPool,
    )

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

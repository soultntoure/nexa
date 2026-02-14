"""
Async engine + session factory.

Contains:
- create_async_engine() with connection pool settings
- AsyncSessionLocal = async_sessionmaker(engine)
- get_session() -> AsyncGenerator[AsyncSession] (for DI)
- init_db() — called at startup to verify connectivity
- close_db() — called at shutdown to dispose engine

Config: reads POSTGRES_URL from Settings
Pool: pool_size=5, max_overflow=10, pool_timeout=30
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.POSTGRES_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Verify connectivity at startup."""
    async with engine.begin() as conn:
        await conn.run_sync(lambda _: None)


async def close_db() -> None:
    """Dispose engine at shutdown."""
    await engine.dispose()

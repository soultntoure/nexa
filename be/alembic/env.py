"""
Alembic async engine configuration.

Contains:
- Imports Base.metadata from app.data.db.base
- Imports all models from app.data.db.models (for autogenerate)
- Configures async engine from Settings.POSTGRES_URL
- run_migrations_online() with async engine
- run_migrations_offline() for SQL generation

Run: alembic revision --autogenerate -m "description"
     alembic upgrade head
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import get_settings
from app.data.db.base import Base

# Import all models so autogenerate discovers every table
import app.data.db.models  # noqa: F401

config = context.config
settings = get_settings()

# Override the ini-file sqlalchemy.url with the real value from Settings
config.set_main_option("sqlalchemy.url", settings.POSTGRES_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL without connecting to the database."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations with an async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode via async engine."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

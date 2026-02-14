"""
Shared Base for all SQLAlchemy models.

Contains:
- Base = declarative_base() — single Base class imported by all models
- This is the target for Alembic's autogenerate (env.py imports Base.metadata)
- All models must inherit from this Base

Keep this file minimal — only the Base declaration.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

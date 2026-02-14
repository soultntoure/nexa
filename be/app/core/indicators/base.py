"""Abstract indicator interface — all rule-based indicators implement this."""

from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from app.agentic_system.schemas.indicators import IndicatorResult


class BaseIndicator(ABC):
    """Base class for deterministic, SQL-based fraud indicators."""

    name: str
    weight: float = 1.0

    @abstractmethod
    async def evaluate(
        self, ctx: dict, session: AsyncSession,
    ) -> IndicatorResult:
        """Run SQL query + Python scoring, return a deterministic result."""

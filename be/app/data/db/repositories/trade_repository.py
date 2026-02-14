"""
Trade CRUD operations.

Contains:
- TradeRepository class (takes AsyncSession)
  - get_by_id(id: UUID) -> Trade | None
  - get_by_customer(customer_id: UUID, limit: int) -> list[Trade]
  - get_recent(customer_id: UUID, days: int) -> list[Trade]
  - get_open_trades(customer_id: UUID) -> list[Trade]
  - get_pnl_summary(customer_id: UUID, days: int) -> dict

Rules: async only, expunge before return.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.models.trade import Trade
from app.data.db.repositories.base_repository import BaseRepository


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TradeRepository(BaseRepository[Trade]):
    """Repository for Trade entity with activity analysis for risk indicators."""

    model_class = Trade

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_customer(
        self, customer_id: uuid.UUID, limit: int = 100
    ) -> list[Trade]:
        """
        Get trades for a customer, ordered by opened_at (most recent first).
        
        Args:
            customer_id: UUID of the customer
            limit: Maximum number of records to return
            
        Returns:
            List of detached Trades
        """
        try:
            stmt = (
                select(Trade)
                .where(Trade.customer_id == customer_id)
                .order_by(desc(Trade.opened_at))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            trades = list(result.scalars().all())
            
            for trade in trades:
                self._expunge(trade)
            
            return trades
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving trades for customer {customer_id}"
            ) from e

    async def get_recent(
        self, customer_id: uuid.UUID, days: int = 30
    ) -> list[Trade]:
        """
        Get recent trades for a customer within specified timeframe.
        
        Args:
            customer_id: UUID of the customer
            days: Number of days to lookback
            
        Returns:
            List of detached Trades within timeframe
        """
        try:
            cutoff = _utcnow() - timedelta(days=days)
            stmt = (
                select(Trade)
                .where(
                    Trade.customer_id == customer_id,
                    Trade.opened_at >= cutoff
                )
                .order_by(desc(Trade.opened_at))
            )
            result = await self.session.execute(stmt)
            trades = list(result.scalars().all())
            
            for trade in trades:
                self._expunge(trade)
            
            return trades
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving recent trades for customer {customer_id}"
            ) from e

    async def get_open_trades(self, customer_id: uuid.UUID) -> list[Trade]:
        """
        Get currently open trades for a customer.
        
        Args:
            customer_id: UUID of the customer
            
        Returns:
            List of detached Trades where closed_at is null
        """
        try:
            stmt = (
                select(Trade)
                .where(
                    Trade.customer_id == customer_id,
                    Trade.closed_at.is_(None)
                )
                .order_by(desc(Trade.opened_at))
            )
            result = await self.session.execute(stmt)
            trades = list(result.scalars().all())
            
            for trade in trades:
                self._expunge(trade)
            
            return trades
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving open trades for customer {customer_id}"
            ) from e

    async def get_pnl_summary(
        self, customer_id: uuid.UUID, days: int = 30
    ) -> dict[str, Any]:
        """
        Get PnL summary for a customer within timeframe.
        
        Args:
            customer_id: UUID of the customer
            days: Number of days to lookback
            
        Returns:
            Dictionary with total_pnl, trade_count, avg_pnl
        """
        try:
            cutoff = _utcnow() - timedelta(days=days)
            stmt = (
                select(
                    func.sum(Trade.pnl).label("total_pnl"),
                    func.count(Trade.id).label("trade_count"),
                    func.avg(Trade.pnl).label("avg_pnl")
                )
                .where(
                    Trade.customer_id == customer_id,
                    Trade.opened_at >= cutoff,
                    Trade.closed_at.is_not(None)  # Only closed trades
                )
            )
            result = await self.session.execute(stmt)
            row = result.one()
            
            return {
                "total_pnl": float(row.total_pnl or Decimal(0)),
                "trade_count": row.trade_count or 0,
                "avg_pnl": float(row.avg_pnl or Decimal(0))
            }
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving PnL summary for customer {customer_id}"
            ) from e

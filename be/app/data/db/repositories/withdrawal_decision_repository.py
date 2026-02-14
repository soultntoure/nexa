"""
WithdrawalDecision CRUD operations.

Contains:
- WithdrawalDecisionRepository class (takes AsyncSession)
  - get_by_id(id: UUID) -> WithdrawalDecision | None
  - get_by_withdrawal(withdrawal_id: UUID) -> WithdrawalDecision | None
  - get_recent(limit: int) -> list[WithdrawalDecision]
  - get_by_decision_type(decision: str, limit: int) -> list[WithdrawalDecision]
  - get_accuracy_stats(days: int) -> dict

Rules: async only, expunge before return.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.models.withdrawal_decision import WithdrawalDecision
from app.data.db.repositories.base_repository import BaseRepository


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WithdrawalDecisionRepository(BaseRepository[WithdrawalDecision]):
    """Repository for WithdrawalDecision entity with analytics methods."""

    model_class = WithdrawalDecision

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_withdrawal(
        self, withdrawal_id: uuid.UUID
    ) -> WithdrawalDecision | None:
        """
        Get decision for a specific withdrawal (1:1 relationship).
        
        Args:
            withdrawal_id: UUID of the withdrawal
            
        Returns:
            Detached WithdrawalDecision if found, None otherwise
        """
        try:
            stmt = select(WithdrawalDecision).where(
                WithdrawalDecision.withdrawal_id == withdrawal_id
            )
            result = await self.session.execute(stmt)
            decision = result.scalar_one_or_none()
            
            if decision:
                self._expunge(decision)
            return decision
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving decision for withdrawal {withdrawal_id}"
            ) from e

    async def get_recent(self, limit: int = 100) -> list[WithdrawalDecision]:
        """
        Get recent decisions, ordered by decided_at (most recent first).
        
        Args:
            limit: Maximum number of decisions to return
            
        Returns:
            List of detached WithdrawalDecisions
        """
        try:
            stmt = (
                select(WithdrawalDecision)
                .order_by(desc(WithdrawalDecision.decided_at))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            decisions = list(result.scalars().all())
            
            for decision in decisions:
                self._expunge(decision)
            
            return decisions
        except SQLAlchemyError as e:
            raise RuntimeError("Error retrieving recent decisions") from e

    async def get_by_decision_type(
        self, decision: str, limit: int = 100
    ) -> list[WithdrawalDecision]:
        """
        Get decisions filtered by type (approve/escalate/block).
        
        Args:
            decision: Decision type to filter by
            limit: Maximum number of decisions to return
            
        Returns:
            List of detached WithdrawalDecisions
        """
        try:
            stmt = (
                select(WithdrawalDecision)
                .where(WithdrawalDecision.decision == decision)
                .order_by(desc(WithdrawalDecision.decided_at))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            decisions = list(result.scalars().all())
            
            for decision_obj in decisions:
                self._expunge(decision_obj)
            
            return decisions
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving {decision} decisions"
            ) from e

    async def get_accuracy_stats(self, days: int = 30) -> dict[str, Any]:
        """
        Get accuracy statistics for decisions within timeframe.
        
        This would typically join with feedback table to calculate accuracy.
        For now, returns basic decision counts.
        
        Args:
            days: Number of days to lookback
            
        Returns:
            Dictionary with decision type counts
        """
        try:
            cutoff = _utcnow() - timedelta(days=days)
            stmt = select(WithdrawalDecision).where(
                WithdrawalDecision.decided_at >= cutoff
            )
            result = await self.session.execute(stmt)
            decisions = list(result.scalars().all())
            
            stats: dict[str, Any] = {
                "total": len(decisions),
                "approve": 0,
                "escalate": 0,
                "block": 0
            }
            
            for decision in decisions:
                if decision.decision in stats:
                    stats[decision.decision] += 1
            
            return stats
        except SQLAlchemyError as e:
            raise RuntimeError("Error retrieving accuracy stats") from e

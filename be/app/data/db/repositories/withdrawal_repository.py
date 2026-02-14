"""
Withdrawal + Decision + IndicatorResult CRUD + listing.

Rules: async only, use selectinload/joinedload for nested relationships.
"""

from __future__ import annotations

import math
import uuid
from typing import Any, NamedTuple

from sqlalchemy import select, func, desc, text
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.models.customer import Customer
from app.data.db.models.evaluation import Evaluation
from app.data.db.models.withdrawal import Withdrawal
from app.data.db.models.withdrawal_decision import WithdrawalDecision
from app.data.db.models.indicator_result import IndicatorResult
from app.data.db.repositories.base_repository import BaseRepository


class WithdrawalPage(NamedTuple):
    """Paginated withdrawal result."""

    items: list[Withdrawal]
    total: int
    page: int
    page_size: int
    total_pages: int


class WithdrawalRepository(BaseRepository[Withdrawal]):
    """Repository for Withdrawal entity with decision and indicator management."""

    model_class = Withdrawal

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, id: uuid.UUID) -> Withdrawal | None:
        """
        Retrieve withdrawal with decision and indicator results eager loaded.
        
        Args:
            id: UUID of the withdrawal
            
        Returns:
            Detached Withdrawal with nested relationships loaded, None if not found
        """
        try:
            stmt = (
                select(Withdrawal)
                .where(Withdrawal.id == id)
                .options(
                    selectinload(Withdrawal.decision),
                    selectinload(Withdrawal.indicator_results),
                )
            )
            result = await self.session.execute(stmt)
            withdrawal = result.scalar_one_or_none()
            
            if withdrawal:
                self._expunge(withdrawal)
            return withdrawal
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving withdrawal {id} with relationships"
            ) from e

    async def get_recent(
        self, customer_id: uuid.UUID, limit: int = 10
    ) -> list[Withdrawal]:
        """
        Get recent withdrawals for a customer, ordered by request time.
        
        Args:
            customer_id: UUID of the customer
            limit: Maximum number of withdrawals to return
            
        Returns:
            List of detached Withdrawals, most recent first
        """
        try:
            stmt = (
                select(Withdrawal)
                .where(Withdrawal.customer_id == customer_id)
                .order_by(desc(Withdrawal.requested_at))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            withdrawals = list(result.scalars().all())
            
            for withdrawal in withdrawals:
                self._expunge(withdrawal)
            
            return withdrawals
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving recent withdrawals for customer {customer_id}"
            ) from e

    async def save_decision(self, decision: WithdrawalDecision) -> WithdrawalDecision:
        """
        Save a withdrawal decision to the database.
        
        Args:
            decision: WithdrawalDecision entity to persist
            
        Returns:
            Saved decision (detached)
        """
        try:
            self.session.add(decision)
            await self.session.commit()
            await self.session.refresh(decision)
            self._expunge(decision)
            return decision
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(
                f"Error saving withdrawal decision for withdrawal {decision.withdrawal_id}"
            ) from e

    async def save_evaluation(self, evaluation: Evaluation) -> Evaluation:
        """Persist an evaluation record."""
        try:
            self.session.add(evaluation)
            await self.session.commit()
            await self.session.refresh(evaluation)
            self._expunge(evaluation)
            return evaluation
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(
                f"Error saving evaluation for withdrawal {evaluation.withdrawal_id}"
            ) from e

    async def save_indicator_results(
        self, results: list[IndicatorResult]
    ) -> None:
        """
        Bulk save indicator results for a withdrawal.
        
        Args:
            results: List of IndicatorResult entities to persist
        """
        try:
            self.session.add_all(results)
            await self.session.commit()
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError("Error saving indicator results") from e

    async def get_recent_decisions(self, limit: int = 100) -> list[WithdrawalDecision]:
        """
        Get recent withdrawal decisions for pattern scanning.
        
        Args:
            limit: Maximum number of decisions to return
            
        Returns:
            List of detached WithdrawalDecisions, most recent first
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

    # ── Indicator query methods ──

    async def get_amount_stats(self, external_id: str) -> dict[str, Any]:
        """Get avg, stddev, count of approved/completed withdrawals for a customer."""
        try:
            result = await self.session.execute(
                text("""
                    SELECT
                        COALESCE(AVG(w.amount), 0) AS avg_amt,
                        COALESCE(STDDEV(w.amount), 0) AS std_amt,
                        COUNT(*) AS total_count
                    FROM withdrawals w
                    JOIN customers c ON c.id = w.customer_id
                    WHERE c.external_id = :customer_id
                      AND w.status IN ('approved', 'completed')
                """),
                {"customer_id": external_id},
            )
            row = result.mappings().first()
            return dict(row) if row else {"avg_amt": 0, "std_amt": 0, "total_count": 0}
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error getting amount stats for customer {external_id}"
            ) from e

    async def get_velocity_counts(self, external_id: str) -> dict[str, int]:
        """Get withdrawal counts in 1h, 24h, 7d, 30d windows."""
        try:
            result = await self.session.execute(
                text("""
                    SELECT
                        COUNT(*) FILTER (
                            WHERE w.requested_at >= NOW() - INTERVAL '1 hour'
                        ) AS count_1h,
                        COUNT(*) FILTER (
                            WHERE w.requested_at >= NOW() - INTERVAL '24 hours'
                        ) AS count_24h,
                        COUNT(*) FILTER (
                            WHERE w.requested_at >= NOW() - INTERVAL '7 days'
                        ) AS count_7d,
                        COUNT(*) FILTER (
                            WHERE w.requested_at >= NOW() - INTERVAL '30 days'
                        ) AS count_30d
                    FROM withdrawals w
                    JOIN customers c ON c.id = w.customer_id
                    WHERE c.external_id = :customer_id
                """),
                {"customer_id": external_id},
            )
            row = result.mappings().first()
            return dict(row) if row else {
                "count_1h": 0,
                "count_24h": 0,
                "count_7d": 0,
                "count_30d": 0,
            }
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error getting velocity counts for customer {external_id}"
            ) from e

    async def get_recipient_info(
        self, external_id: str, recipient_account: str,
    ) -> dict[str, Any] | None:
        """Get customer name, cross-account count, and history for a recipient."""
        try:
            result = await self.session.execute(
                text("""
                    SELECT
                        c.name AS customer_name,
                        (SELECT COUNT(DISTINCT w2.customer_id)
                         FROM withdrawals w2
                         WHERE w2.recipient_account = :recipient_account
                        ) AS cross_account_count,
                        (SELECT COUNT(*)
                         FROM withdrawals w3
                         JOIN customers c2 ON c2.id = w3.customer_id
                         WHERE c2.external_id = :customer_id
                           AND w3.recipient_account = :recipient_account
                        ) AS history_count
                    FROM customers c
                    WHERE c.external_id = :customer_id
                """),
                {"customer_id": external_id, "recipient_account": recipient_account},
            )
            row = result.mappings().first()
            return dict(row) if row else None
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error getting recipient info for customer {external_id}"
            ) from e

    async def get_stats(self) -> dict[str, Any]:
        """Get withdrawal statistics grouped by decision type."""
        try:
            stmt_status = (
                select(
                    Withdrawal.status,
                    func.count(Withdrawal.id).label("count"),
                )
                .group_by(Withdrawal.status)
            )
            result = await self.session.execute(stmt_status)
            rows = result.all()
            stats = {row.status: row.count for row in rows}
            stats["total"] = sum(stats.values())
            return stats
        except SQLAlchemyError as e:
            raise RuntimeError("Error retrieving withdrawal stats") from e

    # ── Listing / pagination ──

    async def list_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        status: str | None = None,
    ) -> WithdrawalPage:
        """Paginated withdrawals with customer data joined."""
        stmt = self._listing_query(search)
        count_stmt = self._count_query(search)
        if status:
            stmt = stmt.where(Withdrawal.status == status)
            count_stmt = count_stmt.where(Withdrawal.status == status)

        total = (await self.session.execute(count_stmt)).scalar_one()
        offset = (page - 1) * page_size
        rows = (
            (await self.session.execute(stmt.offset(offset).limit(page_size)))
            .scalars().unique().all()
        )
        return WithdrawalPage(
            items=list(rows),
            total=total,
            page=page,
            page_size=page_size,
            total_pages=max(1, math.ceil(total / page_size)),
        )

    async def list_all_filtered(
        self,
        search: str | None = None,
        status: str | None = None,
    ) -> list[Withdrawal]:
        """All matching withdrawals (for CSV export)."""
        stmt = self._listing_query(search)
        if status:
            stmt = stmt.where(Withdrawal.status == status)
        return list(
            (await self.session.execute(stmt)).scalars().unique().all()
        )

    @staticmethod
    def _listing_query(search: str | None = None):
        stmt = (
            select(Withdrawal)
            .join(Customer)
            .options(joinedload(Withdrawal.customer))
            .order_by(Withdrawal.requested_at.desc())
        )
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                Customer.name.ilike(pattern) | Customer.email.ilike(pattern)
            )
        return stmt

    @staticmethod
    def _count_query(search: str | None = None):
        stmt = select(func.count()).select_from(Withdrawal).join(Customer)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                Customer.name.ilike(pattern) | Customer.email.ilike(pattern)
            )
        return stmt

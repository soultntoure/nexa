"""
Transaction CRUD operations.

Contains:
- TransactionRepository class (takes AsyncSession)
  - get_by_id(id: UUID) -> Transaction | None
  - get_by_customer(customer_id: UUID, skip: int, limit: int) -> list[Transaction]
  - get_by_type(customer_id: UUID, type: str, limit: int) -> list[Transaction]
  - get_failed_transactions(customer_id: UUID, limit: int) -> list[Transaction]
  - get_recent_by_ip(ip_address: str, limit: int) -> list[Transaction]

Rules: async only, use indexes for efficient queries, expunge before return.
"""

from __future__ import annotations

import uuid

from typing import Any

from sqlalchemy import select, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.models.transaction import Transaction
from app.data.db.repositories.base_repository import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    """Repository for Transaction entity with query methods for analysis."""

    model_class = Transaction

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_customer(
        self, customer_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> list[Transaction]:
        """
        Get transactions for a customer, ordered by timestamp (most recent first).
        
        Args:
            customer_id: UUID of the customer
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            
        Returns:
            List of detached Transactions
        """
        try:
            stmt = (
                select(Transaction)
                .where(Transaction.customer_id == customer_id)
                .order_by(desc(Transaction.timestamp))
                .offset(skip)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            transactions = list(result.scalars().all())
            
            for transaction in transactions:
                self._expunge(transaction)
            
            return transactions
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving transactions for customer {customer_id}"
            ) from e

    async def get_by_type(
        self, customer_id: uuid.UUID, type: str, limit: int = 50
    ) -> list[Transaction]:
        """
        Get transactions for a customer filtered by type.
        
        Args:
            customer_id: UUID of the customer
            type: Transaction type (deposit/withdrawal/trade_pnl)
            limit: Maximum number of records to return
            
        Returns:
            List of detached Transactions, most recent first
        """
        try:
            stmt = (
                select(Transaction)
                .where(
                    Transaction.customer_id == customer_id,
                    Transaction.type == type
                )
                .order_by(desc(Transaction.timestamp))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            transactions = list(result.scalars().all())
            
            for transaction in transactions:
                self._expunge(transaction)
            
            return transactions
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving {type} transactions for customer {customer_id}"
            ) from e

    async def get_failed_transactions(
        self, customer_id: uuid.UUID, limit: int = 20
    ) -> list[Transaction]:
        """
        Get failed transactions for a customer for risk analysis.
        
        Args:
            customer_id: UUID of the customer
            limit: Maximum number of records to return
            
        Returns:
            List of detached failed Transactions, most recent first
        """
        try:
            stmt = (
                select(Transaction)
                .where(
                    Transaction.customer_id == customer_id,
                    Transaction.status == "failed"
                )
                .order_by(desc(Transaction.timestamp))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            transactions = list(result.scalars().all())
            
            for transaction in transactions:
                self._expunge(transaction)
            
            return transactions
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving failed transactions for customer {customer_id}"
            ) from e

    async def get_card_error_stats(self, external_id: str) -> dict[str, int]:
        """Get failed transaction and method switching stats for card_errors indicator."""
        try:
            result = await self.session.execute(
                text("""
                    SELECT
                        COUNT(*) FILTER (
                            WHERE t.status = 'failed'
                              AND t.timestamp >= NOW() - INTERVAL '30 days'
                        ) AS fail_count_30d,
                        COUNT(*) FILTER (
                            WHERE t.error_code IS NOT NULL
                              AND t.timestamp >= NOW() - INTERVAL '30 days'
                        ) AS error_count_30d,
                        COUNT(DISTINCT t.payment_method_id) FILTER (
                            WHERE t.timestamp >= NOW() - INTERVAL '30 days'
                        ) AS distinct_methods_30d
                    FROM transactions t
                    JOIN customers c ON c.id = t.customer_id
                    WHERE c.external_id = :customer_id
                """),
                {"customer_id": external_id},
            )
            row = result.mappings().first()
            return dict(row) if row else {"fail_count_30d": 0, "error_count_30d": 0, "distinct_methods_30d": 0}
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error getting card error stats for customer {external_id}"
            ) from e

    async def get_trading_behavior_stats(self, external_id: str) -> dict[str, Any]:
        """Get deposits, trade count, and PnL for trading_behavior indicator."""
        try:
            result = await self.session.execute(
                text("""
                    WITH cust AS (
                        SELECT id FROM customers WHERE external_id = :customer_id
                    )
                    SELECT
                        COALESCE(SUM(t.amount) FILTER (
                            WHERE t.type = 'deposit' AND t.status = 'success'
                        ), 0) AS total_deposits,
                        (SELECT COUNT(*) FROM trades tr
                         WHERE tr.customer_id = (SELECT id FROM cust)) AS trade_count,
                        (SELECT COALESCE(SUM(tr.pnl), 0) FROM trades tr
                         WHERE tr.customer_id = (SELECT id FROM cust)
                           AND tr.pnl IS NOT NULL) AS total_pnl
                    FROM cust
                    LEFT JOIN transactions t ON t.customer_id = cust.id
                """),
                {"customer_id": external_id},
            )
            row = result.mappings().first()
            return dict(row) if row else {"total_deposits": 0, "trade_count": 0, "total_pnl": 0}
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error getting trading behavior stats for customer {external_id}"
            ) from e

    async def get_recent_by_ip(
        self, ip_address: str, limit: int = 50
    ) -> list[Transaction]:
        """
        Get recent transactions from a specific IP address for fraud detection.
        
        Args:
            ip_address: IP address to search for
            limit: Maximum number of records to return
            
        Returns:
            List of detached Transactions, most recent first
        """
        try:
            stmt = (
                select(Transaction)
                .where(Transaction.ip_address == ip_address)
                .order_by(desc(Transaction.timestamp))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            transactions = list(result.scalars().all())
            
            for transaction in transactions:
                self._expunge(transaction)
            
            return transactions
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving transactions for IP {ip_address}"
            ) from e

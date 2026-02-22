"""DB query functions for each fraud indicator — one async fn per indicator."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.repositories.device_repository import DeviceRepository
from app.data.db.repositories.ip_history_repository import IPHistoryRepository
from app.data.db.repositories.payment_method_repository import PaymentMethodRepository
from app.data.db.repositories.transaction_repository import TransactionRepository
from app.data.db.repositories.withdrawal_repository import WithdrawalRepository


async def query_velocity(ctx: dict, session: AsyncSession) -> dict:
    repo = WithdrawalRepository(session)
    row = await repo.get_velocity_counts(ctx["customer_id"])
    return {
        "count_1h": int(row["count_1h"]),
        "count_24h": int(row["count_24h"]),
        "count_7d": int(row["count_7d"]),
        "count_30d": int(row["count_30d"]),
    }


async def query_amount_anomaly(ctx: dict, session: AsyncSession) -> dict:
    repo = WithdrawalRepository(session)
    row = await repo.get_amount_stats(ctx["customer_id"])
    return {
        "amount": float(ctx.get("amount", 0)),
        "avg": float(row["avg_amt"]),
        "std": float(row["std_amt"]),
        "count": int(row["total_count"]),
    }


async def query_payment_method(ctx: dict, session: AsyncSession) -> dict:
    repo = PaymentMethodRepository(session)
    row = await repo.get_latest_method_risk(ctx["customer_id"])
    if not row:
        return {}
    return {
        "age_days": float(row["age_days"] or 0),
        "is_verified": bool(row["is_verified"]),
        "is_blacklisted": bool(row["is_blacklisted"]),
        "methods_added_30d": int(row["methods_added_30d"] or 0),
    }


async def query_geographic(ctx: dict, session: AsyncSession) -> dict:
    repo = IPHistoryRepository(session)
    rows = await repo.get_recent_with_country(ctx["customer_id"])
    distinct_7d = await repo.get_distinct_countries_7d(ctx["customer_id"])
    historical_countries = await repo.get_distinct_countries_all_time(ctx["customer_id"])
    return {
        "rows": rows,
        "distinct_7d": distinct_7d,
        "historical_countries": historical_countries,
        "customer_country": ctx.get("customer_country", ""),
    }


async def query_device_fingerprint(ctx: dict, session: AsyncSession) -> dict:
    fp = ctx.get("device_fingerprint", "")
    repo = DeviceRepository(session)
    row = await repo.get_fingerprint_risk(ctx["customer_id"], fp)
    if not row:
        return {"fingerprint": fp, "known": False}
    return {
        "is_trusted": bool(row["is_trusted"]),
        "device_age_days": float(row["device_age_days"] or 0),
        "shared_account_count": int(row["shared_account_count"] or 1),
    }


async def query_trading_behavior(ctx: dict, session: AsyncSession) -> dict:
    repo = TransactionRepository(session)
    row = await repo.get_trading_behavior_stats(ctx["customer_id"])
    return {
        "amount": float(ctx.get("amount", 0)),
        "total_deposits": float(row["total_deposits"]),
        "trade_count": int(row["trade_count"]),
        "total_pnl": float(row["total_pnl"]),
    }


async def query_recipient(ctx: dict, session: AsyncSession) -> dict:
    repo = WithdrawalRepository(session)
    row = await repo.get_recipient_info(ctx["customer_id"], ctx.get("recipient_account", ""))
    if not row:
        return {}
    return {
        "customer_name": str(row["customer_name"] or ""),
        "cross_account_count": int(row["cross_account_count"] or 0),
        "history_count": int(row["history_count"] or 0),
        "recipient_name": ctx.get("recipient_name", ""),
    }


async def query_card_errors(ctx: dict, session: AsyncSession) -> dict:
    repo = TransactionRepository(session)
    row = await repo.get_card_error_stats(ctx["customer_id"])
    return {
        "fail_count_30d": int(row["fail_count_30d"]),
        "error_count_30d": int(row["error_count_30d"]),
        "distinct_methods_30d": int(row["distinct_methods_30d"]),
    }

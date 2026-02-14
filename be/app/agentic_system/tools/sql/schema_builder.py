"""Build database schema description programmatically from live DB.

Generates schema documentation for LLM prompts by querying information_schema.
Ensures accuracy and stays in sync with migrations.
"""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def build_schema_description(engine: Engine, tables: list[str]) -> str:
    """Query information_schema to build schema docs for LLM prompt.

    Args:
        engine: SQLAlchemy sync engine
        tables: List of table names to document

    Returns:
        Formatted schema string ready for prompt injection
    """
    schema_parts = ["## Database Schema (from live DB)\n"]

    with engine.connect() as conn:
        for table in tables:
            # Get columns with types and constraints
            result = conn.execute(text(f"""
                SELECT
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = '{table}'
                ORDER BY ordinal_position;
            """))

            columns = result.fetchall()
            if not columns:
                logger.warning(f"Table {table} not found in schema")
                continue

            # Format table header
            schema_parts.append(f"\n### {table}")

            # Build column list
            col_parts = []
            for col_name, data_type, max_len, nullable, default in columns:
                # Format type
                if max_len and data_type in ('character varying', 'character'):
                    type_str = f"VARCHAR({max_len})"
                elif data_type == 'uuid':
                    type_str = "UUID"
                elif data_type == 'boolean':
                    type_str = "BOOL"
                elif data_type == 'numeric':
                    type_str = "NUMERIC"
                elif data_type == 'timestamp with time zone':
                    type_str = "TIMESTAMPTZ"
                elif data_type == 'text':
                    type_str = "TEXT"
                elif data_type == 'jsonb':
                    type_str = "JSONB"
                elif data_type == 'double precision':
                    type_str = "FLOAT"
                else:
                    type_str = data_type.upper()

                # Add constraints
                constraints = []
                if default and 'nextval' not in str(default):
                    constraints.append(f"DEFAULT {default}")
                if nullable == 'NO':
                    # Check if it's a PK or FK via naming convention
                    if col_name == 'id':
                        constraints.append("PK")
                    elif col_name.endswith('_id'):
                        constraints.append("FK")

                constraint_str = f" ({', '.join(constraints)})" if constraints else ""
                col_parts.append(f"{col_name} ({type_str}{constraint_str})")

            schema_parts.append(", ".join(col_parts))

    return "\n".join(schema_parts)


def build_critical_notes() -> str:
    """Return critical schema notes that don't change with migrations."""
    return """\

## CRITICAL Schema Notes

**Two-Layer Status System:**
- `withdrawals.status` = workflow state ('pending' or 'approved') — NOT fraud decision
- `withdrawal_decisions.decision` = fraud assessment ('approved', 'escalated', 'blocked')
- To find flagged withdrawals: `JOIN withdrawal_decisions WHERE decision IN ('blocked', 'escalated')`

**Device Lookups:**
- `devices` table HAS `customer_id` — can JOIN directly on customers
- `withdrawals.device_fingerprint` stores the fingerprint string used for that withdrawal
- To get device details: `JOIN devices ON devices.fingerprint = withdrawals.device_fingerprint`

**IP History:**
- `ip_history` stores location in `geo_json` (JSONB) — use `geo_json->>'country'` or `geo_json->>'city'`
- Use `is_vpn = TRUE` to detect VPN usage

**Time Filters:**
- Always add time filters for "recent", "this week", "this month" queries
- Use `NOW() - INTERVAL '7 days'` for past week
- Use `NOW() - INTERVAL '30 days'` for past month

**Aggregations:**
- Use `COUNT(DISTINCT x)` when counting unique items across JOINs
- Use `BOOL_OR(condition)` to check if ANY row matches a condition
- Always include `LIMIT` to prevent huge result sets (default: 20-50 rows)

**Common Mistakes to Avoid:**
- ❌ `WHERE withdrawals.status = 'blocked'` (status is never 'blocked')
- ❌ `HAVING COUNT(*) > 1` when grouping by country (excludes countries with single flagged customers)
- ❌ Filtering out results with HAVING unless explicitly asked for "more than X"
- ✅ `WHERE withdrawal_decisions.decision IN ('blocked', 'escalated')`
- ✅ `LEFT JOIN ip_history ih ON ih.customer_id = c.id` then `BOOL_OR(ih.is_vpn)`
- ✅ Use GROUP BY for aggregations but avoid unnecessary HAVING filters

**Query Interpretation:**
- "Show flagged customers by country" = GROUP BY country (include ALL countries, even with 1 customer)
- "Show customers with multiple flags" = only include if explicitly means ">1 withdrawals per customer"
- Default: be inclusive — show all results unless specifically asked to filter
"""


def build_pg_cheat_sheet() -> str:
    """Return PostgreSQL-specific syntax notes to prevent common SQL errors."""
    return """\

## PostgreSQL Syntax Cheat Sheet

**Function Mappings (PostgreSQL — NOT MySQL):**
- Use `string_agg(col, ',')` — NOT `group_concat()`
- Use `COUNT(DISTINCT col)` in aggregate calls — NOT inside window functions
- Use `COALESCE(x, default)` for null handling

**JSONB Column Patterns:**
- For JSONB columns (e.g. `alerts.top_indicators`, `alerts.details`, `ip_history.geo_json`):
  - Cast to text first: `top_indicators::text LIKE '%pattern%'`
  - Or expand arrays: `jsonb_array_elements_text(top_indicators)`
  - Do NOT use `= ANY()` on jsonb columns
  - Do NOT use bare `LIKE` on jsonb — always cast with `::text` first

**Column Reference — Commonly Guessed Wrong:**
- `alerts`: columns are `id, customer_id, withdrawal_id, alert_type, risk_score, \
top_indicators (JSONB), details (JSONB), created_at`
  — there is NO `description`, `tags`, or `reasons` column
- `ip_history`: columns are `id, customer_id, ip_address, is_vpn, \
geo_json (JSONB), last_seen`
  — there is NO `country` column. Use `geo_json->>'country'` to get country
"""

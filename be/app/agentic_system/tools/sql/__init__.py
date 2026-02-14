"""SQL tools submodule — all database-facing agent tools live here.

Re-exports from:
  - toolkit.py:  create_sql_toolkit, get_sql_tools, FRAUD_DB_TABLES
  - analysis.py: calculate_statistics, detect_anomaly, calculate_velocity, compare_to_cohort
  - read_only_middleware.py: read_only_sql (LangChain middleware)
"""

from app.agentic_system.tools.sql.analysis import (
    calculate_statistics,
    calculate_velocity,
    compare_to_cohort,
    detect_anomaly,
)
from app.agentic_system.tools.sql.read_only_middleware import read_only_sql
from app.agentic_system.tools.sql.toolkit import (
    FRAUD_DB_TABLES,
    create_sql_toolkit,
    get_sql_tools,
)

__all__ = [
    "create_sql_toolkit",
    "get_sql_tools",
    "FRAUD_DB_TABLES",
    "calculate_statistics",
    "detect_anomaly",
    "calculate_velocity",
    "compare_to_cohort",
    "read_only_sql",
]

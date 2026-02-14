# Agent Tools

Tools that LangChain agents invoke during fraud analysis. Two categories: **SQL-based** (database queries + statistics) and **compute-based** (sandboxed code execution).

---

## Directory Structure

```
tools/
├── sql/                    # All database-facing tools
│   ├── __init__.py         # Re-exports: toolkit, analysis, queries
│   ├── toolkit.py          # SQLDatabaseToolkit setup (4 built-in tools)
│   ├── analysis.py         # @tool statistical functions (z-score, velocity, etc.)
│   └── queries.py          # @tool domain-specific multi-table queries
├── code_executor.py        # @tool execute_python() — sandboxed execution
├── __init__.py
└── README.md
```

---

## SQL Module (`sql/`)

### `toolkit.py` — LangChain SQLDatabaseToolkit

Follows the [LangChain SQL Agent](https://docs.langchain.com) pattern. Wraps Postgres with `SQLDatabase.from_uri()` and produces 4 built-in tools via `SQLDatabaseToolkit`:

| Tool | What it does |
|---|---|
| `sql_db_list_tables` | Lists all table names in the database |
| `sql_db_schema` | Returns `CREATE TABLE` + 3 sample rows for given tables |
| `sql_db_query` | Executes a SQL query, returns rows or error message |
| `sql_db_query_checker` | LLM validates the query before execution |

**Agent workflow:**
```
list_tables → pick relevant → get schema → write query → check query → execute → interpret
                                                            ↑                |
                                                            └── retry on error ←┘
```

**Security:** READ-ONLY Postgres role. Agent prompt forbids DML (INSERT/UPDATE/DELETE/DROP). `sql_db_query_checker` provides LLM-level validation.

### `analysis.py` — Statistical Tools

Custom `@tool` functions for computation SQL can't handle. Agents call these *after* fetching data via `sql_db_query`:

| Tool | Input | Output |
|---|---|---|
| `calculate_statistics` | `list[float]` | mean, std_dev, median, percentiles |
| `detect_anomaly` | value + history | z_score, is_anomaly, percentile |
| `calculate_velocity` | timestamps + windows | events per time window |
| `compare_to_cohort` | value + cohort values | percentile rank, deviation |

### `queries.py` — Domain Convenience Queries

Pre-built multi-table JOINs for common fraud patterns. Reduces agent token usage and errors:

| Tool | What it fetches |
|---|---|
| `query_customer_profile` | Customer + payment methods + devices + IP history |
| `query_withdrawal_context` | Withdrawal + customer + recent history + decision |
| `query_recent_activity` | Withdrawal count, deposit total, trade count, unique IPs |

---

## Code Executor (`code_executor.py`)

Single `@tool execute_python(code: str) -> str` for when agents need:
- Complex pandas/numpy transformations
- Matplotlib chart generation (returns base64 PNG)
- Multi-step statistical analysis beyond `analysis.py`

Delegates to `sandbox/executor.py` with import whitelist and timeout.

---

## How Agents Use These Tools

Each indicator agent receives **all tools** via the `AgentFactory`. Typical flow:

```
1. sql_db_list_tables()                         # discover schema
2. sql_db_schema("withdrawals, transactions")   # understand structure
3. sql_db_query("SELECT ...")                    # fetch raw data
4. calculate_statistics([...])                   # compute stats
5. detect_anomaly(current, history)              # check for outliers
6. → IndicatorResult(score=0.85, reasoning="...") # form judgment
```

---

## Adding a New Tool

1. Decide category: **SQL-facing** → `sql/`, **compute-facing** → new file in `tools/`
2. Decorate with `@tool` from `langchain_core.tools`
3. Accept primitives only (str, float, list, dict) — no ORM objects
4. Return dict or str — must be serializable
5. Register in `sql/__init__.py` or `tools/__init__.py` for discovery
6. `AgentFactory` picks up all exported tools automatically

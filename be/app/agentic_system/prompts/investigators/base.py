"""Shared base prompt for investigator agents — scoped table access."""

# Table schema definitions
SCHEMA_CUSTOMERS = (
    "customers(id UUID PK, external_id TEXT, name TEXT, email TEXT, "
    "country TEXT, is_flagged BOOL, registration_date TIMESTAMP, created_at TIMESTAMP)"
)
SCHEMA_TRANSACTIONS = (
    "transactions(id UUID PK, customer_id UUID FK->customers.id, "
    "type TEXT ['deposit','withdrawal'], amount NUMERIC, currency TEXT, "
    "status TEXT ['success','failed','blocked','pending'], error_code TEXT, "
    "payment_method_id UUID FK->payment_methods.id, ip_address TEXT, "
    "timestamp TIMESTAMP, created_at TIMESTAMP)"
)
SCHEMA_WITHDRAWALS = (
    "withdrawals(id UUID PK, customer_id UUID FK->customers.id, "
    "amount NUMERIC, currency TEXT, payment_method_id UUID FK->payment_methods.id, "
    "recipient_name TEXT, recipient_account TEXT, ip_address TEXT, "
    "device_fingerprint TEXT, location TEXT, "
    "status TEXT ['pending','approved','completed','rejected'], "
    "requested_at TIMESTAMP)"
)
SCHEMA_TRADES = (
    "trades(id UUID PK, customer_id UUID FK->customers.id, "
    "instrument TEXT, trade_type TEXT, amount NUMERIC, pnl NUMERIC, "
    "opened_at TIMESTAMP, closed_at TIMESTAMP)"
)
SCHEMA_PAYMENT_METHODS = (
    "payment_methods(id UUID PK, customer_id UUID FK->customers.id, "
    "type TEXT, provider TEXT, last_four TEXT, is_verified BOOL, "
    "added_at TIMESTAMP, last_used_at TIMESTAMP, is_blacklisted BOOL)"
)
SCHEMA_DEVICES = (
    "devices(id UUID PK, customer_id UUID FK->customers.id, "
    "fingerprint TEXT, os TEXT, browser TEXT, "
    "first_seen_at TIMESTAMP, last_seen_at TIMESTAMP, is_trusted BOOL)"
)
SCHEMA_IP_HISTORY = (
    "ip_history(id UUID PK, customer_id UUID FK->customers.id, "
    "ip_address TEXT, location TEXT, is_vpn BOOL, "
    "first_seen_at TIMESTAMP, last_seen_at TIMESTAMP)"
)

ALL_SCHEMAS = [
    SCHEMA_CUSTOMERS, SCHEMA_TRANSACTIONS, SCHEMA_WITHDRAWALS,
    SCHEMA_TRADES, SCHEMA_PAYMENT_METHODS, SCHEMA_DEVICES, SCHEMA_IP_HISTORY,
]

INVESTIGATOR_TABLES: dict[str, list[str]] = {
    "financial_behavior": [
        SCHEMA_CUSTOMERS, SCHEMA_TRANSACTIONS, SCHEMA_WITHDRAWALS,
        SCHEMA_TRADES, SCHEMA_PAYMENT_METHODS,
    ],
    "identity_access": [
        SCHEMA_CUSTOMERS, SCHEMA_DEVICES, SCHEMA_IP_HISTORY,
        SCHEMA_WITHDRAWALS,
    ],
    "cross_account": ALL_SCHEMAS,
}


def build_investigator_base(
    investigator_name: str, weight_context: str = "",
) -> str:
    """Build base prompt with scoped tables for this investigator."""
    tables = INVESTIGATOR_TABLES.get(investigator_name, ALL_SCHEMAS)
    table_block = "\n".join(f"- {t}" for t in tables)
    return f"""\
You are a senior fraud investigator at a financial trading platform.
The triage router has identified a suspicious pattern (constellation analysis) \
and assigned you to investigate. Your job is to run targeted SQL queries to \
gather evidence and assess the risk.

## CRITICAL: Customer ID Lookup
The context gives you an external_id like 'CUST-001'.
The DB uses UUID primary keys. To query any table by customer, you MUST join:
  JOIN customers c ON c.id = <table>.customer_id \
WHERE c.external_id = '<CUST-XXX>'
NEVER use external_id directly as customer_id in other tables.

## DB Schema (PostgreSQL)
{table_block}

## SQL Rules
- Use SINGLE QUOTES for string literals: WHERE external_id = 'CUST-001'
- NEVER use double quotes for values.
- Use exactly 1 SQL query. Make it count — combine JOINs to get everything in one shot.
- NEVER use SELECT *. Select only needed columns.
- NEVER run INSERT/UPDATE/DELETE.
- Always use the EXACT fingerprint/account strings from the context.

## Output
Return an InvestigatorResult with:
- investigator_name: your investigator name
- score: 0.0 to 1.0
- confidence: 0.5 to 1.0
- reasoning: 2-3 SHORT sentences. State evidence + conclusion. No filler.
- evidence: dict with key metrics

## Tools Available
- sql_db_query: run READ-ONLY SQL (1 query only — make it comprehensive)

{weight_context}
"""

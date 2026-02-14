"""Dump full reasoning from all 3 test customers — rule engine + investigators."""

import json

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

CUSTOMERS = ["CUST-001", "CUST-007", "CUST-011"]
DB_DSN = "postgresql://user:changeme@localhost:15432/fraud_detection"
INVESTIGATE_URL = "http://localhost:18080/api/withdrawals/investigate"


def get_withdrawal(cur, cid: str) -> dict:
    cur.execute(
        "SELECT w.id::text, c.external_id, w.amount::float, w.recipient_name, "
        "w.recipient_account, w.ip_address, w.device_fingerprint, c.country "
        "FROM withdrawals w JOIN customers c ON c.id=w.customer_id "
        "WHERE c.external_id=%s ORDER BY w.requested_at DESC LIMIT 1",
        (cid,),
    )
    return dict(cur.fetchone())


def build_payload(row: dict) -> dict:
    return {
        "withdrawal_id": row["id"],
        "customer_id": row["external_id"],
        "amount": row["amount"],
        "recipient_name": row["recipient_name"],
        "recipient_account": row["recipient_account"],
        "ip_address": row["ip_address"],
        "device_fingerprint": row["device_fingerprint"],
        "customer_country": row["country"],
    }


def print_rule_indicators(data: dict) -> None:
    print("\n  RULE ENGINE INDICATORS:")
    for ind in data.get("indicators", []):
        icon = {"pass": "+", "warn": "~", "fail": "X"}.get(ind.get("status", ""), "?")
        print(f"    [{icon}] {ind['display_name']}: score={ind['score']:.2f}")
        print(f"        {ind['reasoning']}")
        ev = ind.get("evidence", {})
        if ev and not ev.get("mock"):
            print(f"        evidence: {json.dumps(ev, default=str)}")


def print_triage(data: dict) -> None:
    triage = data.get("triage")
    if not triage:
        return
    print(f"\n  TRIAGE ROUTER ({triage['elapsed_s']:.1f}s):")
    print(f"    Constellation: {triage['constellation_analysis']}")
    if not triage["assignments"]:
        print("    Assignments: NONE (all clear)")
    for a in triage["assignments"]:
        print(f"    -> [{a['priority'].upper()}] {a['investigator']}")


def print_investigators(data: dict) -> None:
    investigators = data.get("investigators", [])
    if not investigators:
        print("\n  INVESTIGATORS: none invoked")
        return
    print(f"\n  INVESTIGATORS ({len(investigators)} invoked):")
    for inv in investigators:
        print(
            f"\n    [{inv['score']:.2f} conf={inv['confidence']:.2f}] "
            f"{inv['display_name']}"
        )
        print(f"        {inv['reasoning']}")
        ev = inv.get("evidence", {})
        if ev:
            print(f"        evidence: {json.dumps(ev, default=str)[:400]}")


def main() -> None:
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    for cid in CUSTOMERS:
        row = get_withdrawal(cur, cid)
        payload = build_payload(row)

        # Run investigate (rule engine + triage + investigators)
        inv_resp = httpx.post(INVESTIGATE_URL, json=payload, timeout=120)
        inv_data = inv_resp.json()

        amt = row["amount"]
        print("=" * 80)
        print(
            f"  {cid} | ${amt:,.0f} | "
            f"Investigator: {inv_data['decision'].upper()} (score={inv_data['risk_score']})"
        )
        print(f"  Timings: rule={inv_data.get('rule_engine_elapsed_s', 0)}s "
              f"total={inv_data.get('total_elapsed_s', 0)}s")
        print("=" * 80)

        print_rule_indicators(inv_data)
        print_triage(inv_data)
        print_investigators(inv_data)
        print()

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()

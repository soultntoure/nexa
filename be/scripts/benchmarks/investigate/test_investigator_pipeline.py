"""Test the investigator pipeline and save results to CSV."""

import csv
import json
import os
import time
from datetime import datetime

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

CUSTOMERS = [f"CUST-{i:03d}" for i in range(1, 17)]
DB_DSN = "postgresql://user:changeme@localhost:15432/fraud_detection"
INVESTIGATE_URL = "http://localhost:18080/api/withdrawals/investigate"
OUTPUT_DIR = "outputs/investigator_results"


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


def print_section(title: str) -> None:
    print(f"\n  {title}")


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(OUTPUT_DIR, f"results_{timestamp}.csv")

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    csv_rows = []

    for cid in CUSTOMERS:
        row = get_withdrawal(cur, cid)
        payload = build_payload(row)
        amt = row["amount"]

        # --- Investigator Pipeline ---
        t0 = time.perf_counter()
        inv_resp = httpx.post(INVESTIGATE_URL, json=payload, timeout=120)
        inv_time = round(time.perf_counter() - t0, 2)
        inv_data = inv_resp.json()

        # --- Print ---
        print("=" * 80)
        print(
            f"  {cid} | ${amt:,.0f} | "
            f"Investigator: {inv_data['decision'].upper()} ({inv_data['risk_score']})"
        )
        print(f"  Investigate: {inv_time}s "
              f"(rule={inv_data.get('rule_engine_elapsed_s', 0)}s total={inv_data.get('total_elapsed_s', 0)}s)")
        print("=" * 80)

        # Rule indicators
        print_section("RULE ENGINE INDICATORS:")
        for ind in inv_data.get("indicators", []):
            icon = {"pass": "+", "warn": "~", "fail": "X"}.get(ind.get("status", ""), "?")
            print(f"    [{icon}] {ind['display_name']}: score={ind['score']:.2f}")
            print(f"        {ind['reasoning']}")

        # Triage
        triage = inv_data.get("triage", {})
        print_section(f"TRIAGE ROUTER ({triage.get('elapsed_s', 0):.1f}s):")
        print(f"    Constellation: {triage.get('constellation_analysis', 'N/A')}")
        assignments = triage.get("assignments", [])
        if not assignments:
            print("    Assignments: NONE (all clear)")
        for a in assignments:
            print(f"    -> [{a['priority'].upper()}] {a['investigator']}")

        # Investigators
        investigators = inv_data.get("investigators", [])
        if investigators:
            print_section(f"INVESTIGATORS ({len(investigators)} invoked):")
            for inv in investigators:
                print(
                    f"\n    [{inv['score']:.2f} conf={inv['confidence']:.2f}] "
                    f"{inv['display_name']}"
                )
                print(f"        {inv['reasoning']}")
                ev = inv.get("evidence", {})
                if ev:
                    print(f"        evidence: {json.dumps(ev, default=str)[:400]}")
        else:
            print_section("INVESTIGATORS: none invoked")

        print()

        # --- CSV row ---
        inv_names = [i["investigator_name"] for i in investigators]
        inv_by_name = {i["investigator_name"]: i for i in investigators}

        def _inv_field(name: str, field: str, default: str = "") -> str:
            inv = inv_by_name.get(name)
            if inv is None:
                return default
            return str(inv.get(field, default))

        csv_rows.append({
            "customer_id": cid,
            "amount": amt,
            "investigator_decision": inv_data["decision"],
            "investigator_score": inv_data["risk_score"],
            "investigator_elapsed_s": inv_time,
            "triage_elapsed_s": triage.get("elapsed_s", 0),
            "constellation_analysis": triage.get("constellation_analysis", ""),
            "num_investigators": len(investigators),
            "investigators_invoked": ",".join(inv_names),
            "financial_behavior_score": _inv_field("financial_behavior", "score"),
            "financial_behavior_reasoning": _inv_field("financial_behavior", "reasoning"),
            "financial_behavior_evidence": _inv_field("financial_behavior", "evidence"),
            "identity_access_score": _inv_field("identity_access", "score"),
            "identity_access_reasoning": _inv_field("identity_access", "reasoning"),
            "identity_access_evidence": _inv_field("identity_access", "evidence"),
            "cross_account_score": _inv_field("cross_account", "score"),
            "cross_account_reasoning": _inv_field("cross_account", "reasoning"),
            "cross_account_evidence": _inv_field("cross_account", "evidence"),
        })

    # Write CSV
    if csv_rows:
        fieldnames = list(csv_rows[0].keys())
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"\nCSV saved to: {csv_path}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()

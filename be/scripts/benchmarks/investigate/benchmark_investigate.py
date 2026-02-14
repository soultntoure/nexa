"""Benchmark /api/payout/investigate — thorough multi-iteration benchmark."""

import argparse
import csv
import math
import os
import statistics
import time
from datetime import datetime

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

CUSTOMERS = [f"CUST-{i:03d}" for i in range(1, 17)]
DB_DSN = "postgresql://user:changeme@localhost:15432/fraud_detection"
INVESTIGATE_URL = "http://localhost:18080/api/withdrawals/investigate"
OUTPUT_DIR = "outputs/investigator_benchmark"

# Expected decisions for correctness checking
EXPECTED = {
    "CUST-001": "approved",  # Clean, consistent
    "CUST-002": "approved",  # High-value but trusted
    "CUST-003": "approved",  # Small, clean
    "CUST-004": "approved",  # Regular trader
    "CUST-005": "approved",  # Small, clean
    "CUST-006": "approved",  # Clean mid-tier
    "CUST-007": "approved",  # VPN traveler, legit
    "CUST-008": "approved",  # Clean
    "CUST-009": "approved",  # Clean
    "CUST-010": "approved",  # Rule escalated, investigators clear
    "CUST-011": "blocked",   # Fraud ring + no-trade
    "CUST-012": "blocked",   # Fraud ring
    "CUST-013": "blocked",   # Fraud ring
    "CUST-014": "blocked",   # Fraud ring
    "CUST-015": "blocked",   # ATO scripted extraction
    "CUST-016": "blocked",   # Impossible travel
}


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * (p / 100.0)
    low, high = int(k), min(int(k) + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (k - low)


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


def run_single(client: httpx.Client, payload: dict) -> tuple[dict, float]:
    t0 = time.perf_counter()
    resp = client.post(INVESTIGATE_URL, json=payload, timeout=120)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return resp.json(), elapsed_ms


def print_summary(rows: list[dict], iterations: int) -> None:
    all_latencies = [r["client_elapsed_ms"] for r in rows]
    avg = round(statistics.mean(all_latencies), 1)
    p50 = round(percentile(all_latencies, 50), 1)
    p90 = round(percentile(all_latencies, 90), 1)
    p95 = round(percentile(all_latencies, 95), 1)

    # Group by customer
    by_cust: dict[str, list[dict]] = {}
    for r in rows:
        by_cust.setdefault(r["customer_id"], []).append(r)

    print("\n" + "=" * 90)
    print(f"  INVESTIGATE BENCHMARK — {iterations} iterations x {len(CUSTOMERS)} customers")
    print("=" * 90)

    # Per-customer table
    header = (
        f"{'Customer':<10} {'Expected':<10} {'Decisions':<25} "
        f"{'Consistent':<11} {'Avg ms':>8} {'Std ms':>8} "
        f"{'Avg Score':>10} {'Inv#':>4}"
    )
    print(header)
    print("-" * 90)

    correct_count = 0
    consistent_count = 0

    for cid in CUSTOMERS:
        cust_rows = by_cust.get(cid, [])
        if not cust_rows:
            continue

        lats = [r["client_elapsed_ms"] for r in cust_rows]
        scores = [r["risk_score"] for r in cust_rows]
        decisions = [r["decision"] for r in cust_rows]
        inv_counts = [r["num_investigators"] for r in cust_rows]

        avg_lat = round(statistics.mean(lats), 0)
        std_lat = round(statistics.stdev(lats), 0) if len(lats) > 1 else 0
        avg_score = round(statistics.mean(scores), 3)
        avg_inv = round(statistics.mean(inv_counts), 1)

        unique_decisions = set(decisions)
        consistent = len(unique_decisions) == 1
        if consistent:
            consistent_count += 1

        # Check majority decision against expected
        majority = max(set(decisions), key=decisions.count)
        expected = EXPECTED.get(cid, "?")
        correct = majority == expected
        if correct:
            correct_count += 1

        decision_str = ", ".join(decisions) if iterations <= 3 else majority
        flag = "OK" if consistent else "FLAKY"

        print(
            f"{cid:<10} {expected:<10} {decision_str:<25} "
            f"{flag:<11} {avg_lat:>8.0f} {std_lat:>8.0f} "
            f"{avg_score:>10.3f} {avg_inv:>4.1f}"
        )

    print("-" * 90)

    # Category breakdown
    clean_lats = []
    suspicious_lats = []
    for cid in CUSTOMERS:
        for r in by_cust.get(cid, []):
            if r["num_investigators"] == 0:
                clean_lats.append(r["client_elapsed_ms"])
            else:
                suspicious_lats.append(r["client_elapsed_ms"])

    print(f"\nLatency overall:  avg={avg}ms  p50={p50}ms  p90={p90}ms  p95={p95}ms")
    if clean_lats:
        print(
            f"  Clean (0 inv):     avg={statistics.mean(clean_lats):.0f}ms  "
            f"n={len(clean_lats)}"
        )
    if suspicious_lats:
        print(
            f"  Suspicious (inv):  avg={statistics.mean(suspicious_lats):.0f}ms  "
            f"n={len(suspicious_lats)}"
        )

    print(f"\nAccuracy:    {correct_count}/{len(CUSTOMERS)} correct vs expected")
    print(f"Consistency: {consistent_count}/{len(CUSTOMERS)} same decision across all iterations")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark /investigate")
    parser.add_argument("--iterations", "-n", type=int, default=3)
    args = parser.parse_args()
    iterations = args.iterations

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(OUTPUT_DIR, timestamp)
    os.makedirs(out_dir, exist_ok=True)

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    targets = {cid: get_withdrawal(cur, cid) for cid in CUSTOMERS}
    cur.close()
    conn.close()

    rows: list[dict] = []
    client = httpx.Client()

    for iteration in range(1, iterations + 1):
        print(f"\n--- Iteration {iteration}/{iterations} ---")
        for cid in CUSTOMERS:
            payload = build_payload(targets[cid])
            data, elapsed_ms = run_single(client, payload)

            triage = data.get("triage", {})
            investigators = data.get("investigators", [])

            rows.append({
                "iteration": iteration,
                "customer_id": cid,
                "amount": targets[cid]["amount"],
                "decision": data["decision"],
                "risk_score": data["risk_score"],
                "rule_score": data.get("rule_engine_score", ""),
                "client_elapsed_ms": elapsed_ms,
                "total_pipeline_s": data["total_elapsed_s"],
                "rule_engine_s": data["rule_engine_elapsed_s"],
                "triage_s": triage.get("elapsed_s", 0),
                "num_investigators": len(investigators),
                "investigators_invoked": ",".join(
                    i["investigator_name"] for i in investigators
                ),
                "triage_decision": triage.get("decision", "skipped"),
                "triage_confidence": triage.get("confidence", 0),
            })

            expected = EXPECTED.get(cid, "?")
            mark = "+" if data["decision"] == expected else "X"
            print(
                f"  [{mark}] {cid}: {data['decision']:<10} "
                f"score={data['risk_score']:.2f}  "
                f"{elapsed_ms:.0f}ms  inv={len(investigators)}"
            )

    client.close()

    # Write raw CSV
    csv_path = os.path.join(out_dir, "investigate_benchmark.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print_summary(rows, iterations)
    print(f"\nCSV saved: {csv_path}")


if __name__ == "__main__":
    main()

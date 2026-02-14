"""Test ALL API endpoints after route refactoring. Saves results to outputs/endpoint_tests/."""

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASE = "http://localhost:18080/api"
OUT = Path("outputs/endpoint_tests")
OUT.mkdir(parents=True, exist_ok=True)

results: list[dict] = []


def record(name: str, method: str, url: str, status: int, body: dict | str | None, elapsed: float, passed: bool, note: str = ""):
    entry = {
        "test": name,
        "method": method,
        "url": url,
        "status": status,
        "elapsed_s": round(elapsed, 3),
        "passed": passed,
        "note": note,
        "response_preview": str(body)[:500] if body else None,
    }
    results.append(entry)
    icon = "PASS" if passed else "FAIL"
    print(f"[{icon}] {name} — {status} — {elapsed:.2f}s {note}")


def test_health():
    t0 = time.perf_counter()
    r = httpx.get(f"{BASE}/health", timeout=10)
    elapsed = time.perf_counter() - t0
    body = r.json()
    record("GET /health", "GET", f"{BASE}/health", r.status_code, body, elapsed,
           r.status_code == 200 and body.get("status") == "ok")


def test_dashboard_stats():
    t0 = time.perf_counter()
    r = httpx.get(f"{BASE}/dashboard/stats", timeout=15)
    elapsed = time.perf_counter() - t0
    body = r.json()
    record("GET /dashboard/stats", "GET", f"{BASE}/dashboard/stats", r.status_code, body, elapsed,
           r.status_code == 200)


def test_alerts():
    t0 = time.perf_counter()
    r = httpx.get(f"{BASE}/alerts", timeout=15)
    elapsed = time.perf_counter() - t0
    body = r.json()
    passed = r.status_code == 200 and "alerts" in body and "patterns" in body
    record("GET /alerts", "GET", f"{BASE}/alerts", r.status_code, body, elapsed, passed)
    return body


def test_alerts_bulk_action(alert_ids: list[str]):
    # Test dismiss with real or fake IDs
    ids = alert_ids[:1] if alert_ids else [str(uuid.uuid4())]
    payload = {"alert_ids": ids, "action": "dismiss"}
    t0 = time.perf_counter()
    r = httpx.post(f"{BASE}/alerts/bulk-action", json=payload, timeout=15)
    elapsed = time.perf_counter() - t0
    body = r.json()
    passed = r.status_code == 200 and "status" in body
    record("POST /alerts/bulk-action", "POST", f"{BASE}/alerts/bulk-action", r.status_code, body, elapsed, passed)


def test_queue():
    t0 = time.perf_counter()
    r = httpx.get(f"{BASE}/payout/queue", timeout=15)
    elapsed = time.perf_counter() - t0
    body = r.json()
    passed = r.status_code == 200 and "items" in body
    record("GET /payout/queue", "GET", f"{BASE}/payout/queue", r.status_code, body, elapsed, passed)


def test_evaluate():
    payload = {
        "withdrawal_id": str(uuid.uuid4()),
        "customer_id": "CUST-001",
        "amount": 5000.0,
        "recipient_name": "Test User",
        "recipient_account": "ACC-TEST-001",
        "ip_address": "192.168.1.1",
        "device_fingerprint": "fp-test-001",
        "customer_country": "USA",
        "run_llm_comparison": False,
    }
    t0 = time.perf_counter()
    r = httpx.post(f"{BASE}/payout/evaluate", json=payload, timeout=60)
    elapsed = time.perf_counter() - t0
    body = r.json()
    passed = r.status_code == 200 and "decision" in body and "risk_score" in body
    record("POST /payout/evaluate", "POST", f"{BASE}/payout/evaluate", r.status_code, body, elapsed, passed,
           note=f"decision={body.get('decision')} score={body.get('risk_score')}")
    return body


def test_get_evaluation(withdrawal_id: str):
    t0 = time.perf_counter()
    r = httpx.get(f"{BASE}/payout/evaluate/{withdrawal_id}", timeout=15)
    elapsed = time.perf_counter() - t0
    body = r.json()
    passed = r.status_code in (200, 404)  # 404 expected for unknown IDs
    record("GET /payout/evaluate/{id}", "GET", f"{BASE}/payout/evaluate/{withdrawal_id}", r.status_code, body, elapsed, passed)


def test_investigate():
    payload = {
        "withdrawal_id": str(uuid.uuid4()),
        "customer_id": "CUST-005",
        "amount": 15000.0,
        "recipient_name": "Suspicious Recipient",
        "recipient_account": "ACC-SUSP-001",
        "ip_address": "10.0.0.1",
        "device_fingerprint": "fp-susp-001",
        "customer_country": "RUS",
    }
    t0 = time.perf_counter()
    r = httpx.post(f"{BASE}/payout/investigate", json=payload, timeout=120)
    elapsed = time.perf_counter() - t0
    body = r.json()
    passed = r.status_code == 200 and "decision" in body
    record("POST /payout/investigate", "POST", f"{BASE}/payout/investigate", r.status_code, body, elapsed, passed,
           note=f"decision={body.get('decision')} score={body.get('risk_score')}")


def test_decision():
    # Use fake IDs — expect it to handle gracefully
    payload = {
        "withdrawal_id": str(uuid.uuid4()),
        "evaluation_id": str(uuid.uuid4()),
        "officer_id": "officer-test",
        "action": "approved",
        "reason": "Test approval",
    }
    t0 = time.perf_counter()
    r = httpx.post(f"{BASE}/payout/decision", json=payload, timeout=15)
    elapsed = time.perf_counter() - t0
    body = r.json()
    passed = r.status_code == 200 and body.get("action") == "approved"
    record("POST /payout/decision", "POST", f"{BASE}/payout/decision", r.status_code, body, elapsed, passed)


def test_query():
    payload = {"question": "Show me a summary of all transactions"}
    t0 = time.perf_counter()
    r = httpx.post(f"{BASE}/query", json=payload, timeout=60)
    elapsed = time.perf_counter() - t0
    # Now returns SSE stream
    passed = r.status_code == 200
    content_type = r.headers.get("content-type", "")
    note = f"content-type={content_type}"
    body_text = r.text[:500]
    record("POST /query (SSE)", "POST", f"{BASE}/query", r.status_code, body_text, elapsed, passed, note=note)


def test_transactions():
    t0 = time.perf_counter()
    r = httpx.get(f"{BASE}/transactions", timeout=15)
    elapsed = time.perf_counter() - t0
    body = r.json()
    passed = r.status_code == 200
    record("GET /transactions", "GET", f"{BASE}/transactions", r.status_code, body, elapsed, passed)


def test_investigate_evidence(withdrawal_id: str):
    t0 = time.perf_counter()
    r = httpx.get(f"{BASE}/payout/investigate/{withdrawal_id}", timeout=15)
    elapsed = time.perf_counter() - t0
    body = r.json()
    # May 404 if no investigation data — that's expected for some IDs
    passed = r.status_code in (200, 404)
    record("GET /payout/investigate/{id}", "GET", f"{BASE}/payout/investigate/{withdrawal_id}",
           r.status_code, body, elapsed, passed, note=f"status={r.status_code}")


def main():
    print("=" * 60)
    print(f"Endpoint Test Suite — {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # 1. Health
    test_health()

    # 2. Dashboard
    test_dashboard_stats()

    # 3. Alerts (refactored)
    alerts_data = test_alerts()
    alert_ids = [a["id"] for a in alerts_data.get("alerts", [])]
    test_alerts_bulk_action(alert_ids)

    # 4. Queue
    test_queue()

    # 5. Evaluate (refactored)
    eval_result = test_evaluate()
    if eval_result and eval_result.get("evaluation_id"):
        # Try to find the withdrawal_id from the request we made
        # The evaluate endpoint doesn't return withdrawal_id, so we skip get_evaluation for now
        pass

    # 6. Get evaluation — random UUID will 404 (expected, tests error handling)
    test_get_evaluation(str(uuid.uuid4()))

    # 7. Investigate
    test_investigate()

    # 8. Decision
    test_decision()

    # 9. Query (refactored — now SSE)
    test_query()

    # 10. Transactions
    test_transactions()

    # 11. Investigate evidence
    test_investigate_evidence(str(uuid.uuid4()))

    # Summary
    print("\n" + "=" * 60)
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    print(f"TOTAL: {total} | PASSED: {passed} | FAILED: {failed}")
    print("=" * 60)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = OUT / f"endpoint_test_{timestamp}.json"
    with open(out_file, "w") as f:
        json.dump({
            "run_at": datetime.now(timezone.utc).isoformat(),
            "total": total,
            "passed": passed,
            "failed": failed,
            "results": results,
        }, f, indent=2)
    print(f"\nResults saved to: {out_file}")

    # Also save a readable summary
    summary_file = OUT / f"endpoint_test_{timestamp}.md"
    with open(summary_file, "w") as f:
        f.write(f"# Endpoint Test Results — {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write(f"**Total: {total} | Passed: {passed} | Failed: {failed}**\n\n")
        f.write("| Test | Status | HTTP | Latency | Note |\n")
        f.write("|------|--------|------|---------|------|\n")
        for r in results:
            icon = "PASS" if r["passed"] else "FAIL"
            f.write(f"| {r['test']} | {icon} | {r['status']} | {r['elapsed_s']}s | {r.get('note', '')} |\n")
    print(f"Summary saved to: {summary_file}")


if __name__ == "__main__":
    main()

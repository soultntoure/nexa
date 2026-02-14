"""Benchmark the render_chart tool — 20 queries testing LLM-driven chart generation.

Tests whether the LLM correctly:
1. Produces charts for chart-worthy queries (bar/line/pie)
2. Skips charts for non-chart queries (single numbers, yes/no)

Saves CSV to outputs/chart_benchmark/.
"""

import asyncio
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASE_URL = "http://localhost:18080/api/query/chat"
OUTPUT_DIR = Path("outputs/chart_benchmark")

# 20 test cases: 15 should chart, 5 should NOT chart
TEST_CASES: list[dict] = [
    # === SHOULD PRODUCE BAR CHART (7 cases) ===
    {
        "id": 1,
        "question": "Who are our top 10 withdrawing customers?",
        "expect_chart": True,
        "expect_type": "bar",
        "category": "top-N ranked",
    },
    {
        "id": 2,
        "question": "Show me the top 5 customers by number of withdrawals",
        "expect_chart": True,
        "expect_type": "bar",
        "category": "top-N count",
    },
    {
        "id": 3,
        "question": "Compare the total withdrawal amounts by country",
        "expect_chart": True,
        "expect_type": "bar",
        "category": "categorical comparison",
    },
    {
        "id": 4,
        "question": "What are the average risk scores per customer?",
        "expect_chart": True,
        "expect_type": "bar",
        "category": "per-entity metric",
    },
    {
        "id": 5,
        "question": "Show the number of withdrawals per payment method",
        "expect_chart": True,
        "expect_type": "bar",
        "category": "categorical count",
    },
    {
        "id": 6,
        "question": "Which customers have the most devices?",
        "expect_chart": True,
        "expect_type": "bar",
        "category": "top-N devices",
    },
    {
        "id": 7,
        "question": "Show me blocked vs approved withdrawal counts by country",
        "expect_chart": True,
        "expect_type": "bar",
        "category": "grouped comparison",
    },
    # === SHOULD PRODUCE PIE CHART (4 cases) ===
    {
        "id": 8,
        "question": "What is the breakdown of withdrawal statuses?",
        "expect_chart": True,
        "expect_type": "pie",
        "category": "status distribution",
    },
    {
        "id": 9,
        "question": "Show the distribution of payment methods used",
        "expect_chart": True,
        "expect_type": "pie",
        "category": "method distribution",
    },
    {
        "id": 10,
        "question": "What percentage of evaluations are approved vs blocked vs escalated?",
        "expect_chart": True,
        "expect_type": "pie",
        "category": "decision distribution",
    },
    {
        "id": 11,
        "question": "Show me the share of total withdrawal amount by payment method",
        "expect_chart": True,
        "expect_type": "pie",
        "category": "amount share",
    },
    # === SHOULD PRODUCE LINE CHART (4 cases) ===
    {
        "id": 12,
        "question": "Show me the daily withdrawal count over the past 2 weeks",
        "expect_chart": True,
        "expect_type": "line",
        "category": "daily trend",
    },
    {
        "id": 13,
        "question": "What is the trend of total withdrawal amounts by day?",
        "expect_chart": True,
        "expect_type": "line",
        "category": "amount trend",
    },
    {
        "id": 14,
        "question": "Plot the number of new customers registered per day",
        "expect_chart": True,
        "expect_type": "line",
        "category": "registration trend",
    },
    {
        "id": 15,
        "question": "Show the daily average risk score trend",
        "expect_chart": True,
        "expect_type": "line",
        "category": "risk trend",
    },
    # === SHOULD NOT PRODUCE CHART (5 cases) ===
    {
        "id": 16,
        "question": "How many customers are there in total?",
        "expect_chart": False,
        "expect_type": None,
        "category": "single number",
    },
    {
        "id": 17,
        "question": "What is the total amount of all withdrawals?",
        "expect_chart": False,
        "expect_type": None,
        "category": "single aggregate",
    },
    {
        "id": 18,
        "question": "Is there a customer named James Wilson?",
        "expect_chart": False,
        "expect_type": None,
        "category": "yes/no lookup",
    },
    {
        "id": 19,
        "question": "What is James Wilson's email address?",
        "expect_chart": False,
        "expect_type": None,
        "category": "single record lookup",
    },
    {
        "id": 20,
        "question": "Hello, what can you help me with?",
        "expect_chart": False,
        "expect_type": None,
        "category": "greeting (no SQL)",
    },
]


async def run_test(client: httpx.AsyncClient, case: dict) -> dict:
    """Send a query, collect SSE events, check for chart emission."""
    chart_event: dict | None = None
    answer_text = ""
    error: str | None = None
    event_count = 0
    ttft: float | None = None

    start = time.perf_counter()
    try:
        async with client.stream(
            "POST",
            BASE_URL,
            json={
                "question": case["question"],
                "session_id": f"chart_bench_{case['id']}",
                "visualize": True,
            },
            timeout=120.0,
        ) as resp:
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                event_count += 1
                if ttft is None:
                    ttft = time.perf_counter() - start
                try:
                    ev = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue

                if ev.get("type") == "chart":
                    chart_event = ev.get("chart", {})
                elif ev.get("type") == "answer":
                    answer_text = ev.get("content", "")
                elif ev.get("type") == "error":
                    error = ev.get("message", "")

    except Exception as exc:
        error = str(exc)

    total_s = time.perf_counter() - start

    # Evaluate result
    got_chart = chart_event is not None
    got_type = chart_event.get("chart_type") if chart_event else None
    got_rows = len(chart_event.get("rows", [])) if chart_event else 0

    chart_correct = got_chart == case["expect_chart"]
    type_correct = (
        got_type == case["expect_type"]
        if case["expect_chart"] and got_chart
        else True  # don't penalize type if chart presence is wrong
    )

    return {
        "id": case["id"],
        "question": case["question"],
        "category": case["category"],
        "expect_chart": case["expect_chart"],
        "expect_type": case["expect_type"] or "",
        "got_chart": got_chart,
        "got_type": got_type or "",
        "got_rows": got_rows,
        "chart_correct": chart_correct,
        "type_correct": type_correct,
        "pass": chart_correct,  # main pass/fail = did it chart when it should?
        "ttft_s": round(ttft or 0, 3),
        "total_s": round(total_s, 3),
        "answer_preview": answer_text[:200],
        "error": error or "",
        "event_count": event_count,
    }


async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    print(f"\n{'='*70}")
    print("  CHART TOOL BENCHMARK — 20 test cases")
    print(f"{'='*70}\n")

    async with httpx.AsyncClient() as client:
        for case in TEST_CASES:
            print(f"  [{case['id']:>2}/20] {case['question'][:60]}...")
            result = await run_test(client, case)
            results.append(result)

            status = "PASS" if result["pass"] else "FAIL"
            chart_info = (
                f"chart={result['got_type']}({result['got_rows']} rows)"
                if result["got_chart"]
                else "no chart"
            )
            print(
                f"         {status} | {chart_info} | "
                f"{result['total_s']:.1f}s"
                f"{' | TYPE MISMATCH: expected ' + str(result['expect_type']) if not result['type_correct'] else ''}"
            )
            if result["error"]:
                print(f"         ERROR: {result['error'][:100]}")

    # Summary
    total = len(results)
    chart_pass = sum(1 for r in results if r["chart_correct"])
    type_pass = sum(
        1 for r in results
        if r["expect_chart"] and r["got_chart"] and r["type_correct"]
    )
    should_chart = sum(1 for r in results if r["expect_chart"])
    should_not = total - should_chart
    true_pos = sum(1 for r in results if r["expect_chart"] and r["got_chart"])
    true_neg = sum(1 for r in results if not r["expect_chart"] and not r["got_chart"])
    false_neg = sum(1 for r in results if r["expect_chart"] and not r["got_chart"])
    false_pos = sum(1 for r in results if not r["expect_chart"] and r["got_chart"])
    avg_latency = sum(r["total_s"] for r in results) / total

    print(f"\n{'='*70}")
    print("  RESULTS")
    print(f"{'='*70}")
    print(f"  Chart presence accuracy : {chart_pass}/{total} ({chart_pass/total*100:.0f}%)")
    print(f"  Chart type accuracy     : {type_pass}/{should_chart} (of cases that should chart)")
    print(f"  True positives          : {true_pos}/{should_chart}")
    print(f"  True negatives          : {true_neg}/{should_not}")
    print(f"  False negatives (missed): {false_neg}/{should_chart}")
    print(f"  False positives (extra) : {false_pos}/{should_not}")
    print(f"  Avg latency             : {avg_latency:.1f}s")

    # Save CSV
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    csv_path = OUTPUT_DIR / f"chart_benchmark_{ts}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    # Save JSON with summary
    json_path = OUTPUT_DIR / f"chart_benchmark_{ts}.json"
    json_path.write_text(json.dumps({
        "timestamp": ts,
        "total_cases": total,
        "chart_presence_accuracy": f"{chart_pass}/{total}",
        "chart_type_accuracy": f"{type_pass}/{should_chart}",
        "true_positives": true_pos,
        "true_negatives": true_neg,
        "false_negatives": false_neg,
        "false_positives": false_pos,
        "avg_latency_s": round(avg_latency, 3),
        "results": results,
    }, indent=2))

    print(f"\n  CSV saved: {csv_path}")
    print(f"  JSON saved: {json_path}")


if __name__ == "__main__":
    asyncio.run(main())

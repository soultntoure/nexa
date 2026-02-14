"""Benchmark the /api/query/chat SSE endpoint across 3 difficulty levels.

Measures total response time and time-to-first-token (TTFT) for each question.
Saves results to outputs/chat_benchmark/.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASE_URL = "http://localhost:18080/api/query/chat"
OUTPUT_DIR = Path("outputs/chat_benchmark")

QUESTIONS: dict[str, list[str]] = {
    "simple": [
        "How many blocked transactions are there?",
        "What is the total number of evaluations?",
        "Show me approved withdrawals",
    ],
    "medium": [
        "Which customers have the highest risk scores and why?",
        "What are the most common fraud indicators across all evaluations?",
        "Compare blocked vs escalated transactions by amount",
    ],
    "complex": [
        "Analyze the correlation between geographic indicators and device fingerprint anomalies across all customers",
        "Which customers show patterns consistent with account takeover based on their transaction history and indicator scores?",
        "Provide a comprehensive risk assessment comparing all customers, including their indicator breakdowns and fraud patterns",
    ],
}


async def run_question(client: httpx.AsyncClient, question: str) -> dict:
    """Send a question and measure TTFT + total response time."""
    events: list[dict] = []
    ttft: float | None = None

    start = time.perf_counter()
    async with client.stream(
        "POST", BASE_URL, json={"question": question}, timeout=120.0
    ) as resp:
        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            if ttft is None:
                ttft = time.perf_counter() - start
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                events.append({"raw": line[6:]})

    total = time.perf_counter() - start

    answer = ""
    tools_used: list[str] = []
    error: str | None = None
    for ev in events:
        if ev.get("type") == "answer":
            answer = ev.get("content", "")
        elif ev.get("type") == "done":
            tools_used = ev.get("tools_used", [])
        elif ev.get("type") == "error":
            error = ev.get("message", "")

    return {
        "question": question,
        "ttft_s": round(ttft or 0, 3),
        "total_s": round(total, 3),
        "answer_preview": answer[:300],
        "tools_used": tools_used,
        "error": error,
        "event_count": len(events),
    }


async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_results: dict[str, list[dict]] = {}
    summary_lines: list[str] = []

    async with httpx.AsyncClient() as client:
        for level, questions in QUESTIONS.items():
            print(f"\n{'='*60}")
            print(f"  Level: {level.upper()}")
            print(f"{'='*60}")
            level_results: list[dict] = []

            for i, q in enumerate(questions, 1):
                print(f"\n  [{i}/{len(questions)}] {q[:70]}...")
                result = await run_question(client, q)
                level_results.append(result)

                status = "ERROR" if result["error"] else "OK"
                print(f"    TTFT: {result['ttft_s']:.3f}s | Total: {result['total_s']:.3f}s | {status}")

            all_results[level] = level_results

            avg_ttft = sum(r["ttft_s"] for r in level_results) / len(level_results)
            avg_total = sum(r["total_s"] for r in level_results) / len(level_results)
            summary_lines.append(f"| {level:<8} | {avg_ttft:>8.3f}s | {avg_total:>8.3f}s |")

    # Print summary table
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    print(f"| {'Level':<8} | {'Avg TTFT':>9} | {'Avg Total':>9} |")
    print(f"|{'-'*10}|{'-'*11}|{'-'*11}|")
    for line in summary_lines:
        print(line)

    # Save results
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    results_path = OUTPUT_DIR / f"chat_benchmark_{ts}.json"
    results_path.write_text(json.dumps({
        "timestamp": ts,
        "base_url": BASE_URL,
        "results": all_results,
        "summary": {
            level: {
                "avg_ttft_s": round(sum(r["ttft_s"] for r in res) / len(res), 3),
                "avg_total_s": round(sum(r["total_s"] for r in res) / len(res), 3),
            }
            for level, res in all_results.items()
        },
    }, indent=2))
    print(f"\nResults saved to {results_path}")


if __name__ == "__main__":
    asyncio.run(main())

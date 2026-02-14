"""Benchmark /api/query endpoints — keyword search + analyst chat streaming.

Tests both endpoints with complex fraud detection questions, measures:
- Keyword endpoint: latency, correctness, data completeness
- Chat endpoint: TTFT, total latency, token throughput, SSE events

Saves detailed CSV results to outputs/query_benchmark/<timestamp>/
"""

import argparse
import csv
import json
import os
import time
from datetime import datetime

import httpx

API_BASE = "http://localhost:18080/api"
KEYWORD_URL = f"{API_BASE}/query"
CHAT_URL = f"{API_BASE}/query/chat"
OUTPUT_DIR = "outputs/query_benchmark"
TIMEOUT = 90.0

# Test questions covering different query types
KEYWORD_QUESTIONS = [
    "Show me all blocked transactions",
    "What's the auto-approval rate?",
    "Show high risk transactions",
    "What blocked transactions do we have?",
    "Show me escalated withdrawals",
    "Give me an overview of all transactions",
    "Show me transactions flagged by trading behavior",
    "Show me geographic violations",
    "What crypto withdrawals are there?",
    "Show transactions by country",
]

CHAT_QUESTIONS = [
    "How many customers have been blocked in the last 24 hours?",
    "Show me all withdrawals over $5000 with their risk scores",
    "Which customers have failed transactions in the past week?",
    "Find customers who share the same device fingerprint",
    "What's the average withdrawal amount by decision type?",
    "Show me all VPN users with high risk scores",
    "Which countries have the highest fraud rate?",
    "Find customers with multiple payment methods",
    "Show me withdrawals with device fingerprint scores above 0.7",
    "What's the total amount of blocked withdrawals?",
    "Find fraud patterns with shared recipients",
    "Which customers have made withdrawals in multiple countries?",
    "Show me the top 5 highest risk customers",
    "Find customers with trading behavior scores below 0.3",
    "What's the correlation between velocity and fraud?",
]


def run_keyword_query(question: str, run_id: int) -> dict:
    """Execute keyword query endpoint, measure latency."""
    t0 = time.perf_counter()
    try:
        resp = httpx.post(
            KEYWORD_URL,
            json={"question": question, "history": []},
            timeout=TIMEOUT,
        )
        latency = time.perf_counter() - t0
        resp.raise_for_status()
        data = resp.json()

        return {
            "run_id": run_id,
            "question": question,
            "latency_s": round(latency, 3),
            "status": "success",
            "answer_length": len(data.get("answer", "")),
            "data_count": len(data.get("data", [])),
            "sql_executed": data.get("sql_executed", ""),
            "error": None,
        }
    except Exception as exc:
        latency = time.perf_counter() - t0
        return {
            "run_id": run_id,
            "question": question,
            "latency_s": round(latency, 3),
            "status": "error",
            "answer_length": 0,
            "data_count": 0,
            "sql_executed": None,
            "error": str(exc),
        }


def run_chat_query(question: str, run_id: int) -> dict:
    """Execute streaming chat endpoint, measure TTFT + total latency."""
    t0 = time.perf_counter()
    ttft = None
    token_count = 0
    events = []
    tools_used = []
    full_answer = ""

    try:
        with httpx.stream(
            "POST",
            CHAT_URL,
            json={"question": question, "history": []},
            timeout=TIMEOUT,
        ) as resp:
            resp.raise_for_status()

            for line in resp.iter_lines():
                if not line.startswith("data: "):
                    continue

                try:
                    event = json.loads(line[6:])  # Strip "data: " prefix
                    event_type = event.get("type", "unknown")
                    events.append(event_type)

                    if event_type == "token":
                        token_count += 1
                        if ttft is None:
                            ttft = time.perf_counter() - t0

                    elif event_type == "tool_start":
                        tools_used.append(event.get("name", "unknown"))

                    elif event_type == "answer":
                        full_answer = event.get("content", "")

                    elif event_type == "done":
                        break

                    elif event_type == "error":
                        raise RuntimeError(event.get("message", "Unknown error"))

                except json.JSONDecodeError:
                    continue

        total_latency = time.perf_counter() - t0

        return {
            "run_id": run_id,
            "question": question,
            "latency_s": round(total_latency, 3),
            "ttft_s": round(ttft, 3) if ttft else None,
            "token_count": token_count,
            "tokens_per_sec": round(token_count / total_latency, 1) if token_count > 0 else 0,
            "events": len(events),
            "tools_used": ",".join(set(tools_used)),
            "answer_length": len(full_answer),
            "status": "success",
            "error": None,
        }

    except Exception as exc:
        total_latency = time.perf_counter() - t0
        return {
            "run_id": run_id,
            "question": question,
            "latency_s": round(total_latency, 3),
            "ttft_s": None,
            "token_count": 0,
            "tokens_per_sec": 0,
            "events": 0,
            "tools_used": "",
            "answer_length": 0,
            "status": "error",
            "error": str(exc),
        }


def run_keyword_benchmark(iterations: int) -> list[dict]:
    """Run keyword endpoint benchmark."""
    results = []
    total = len(KEYWORD_QUESTIONS) * iterations

    print(f"\n{'='*80}")
    print(f"KEYWORD ENDPOINT BENCHMARK — {total} queries ({iterations} iterations × {len(KEYWORD_QUESTIONS)} questions)")
    print(f"{'='*80}\n")

    for run_id in range(1, iterations + 1):
        print(f"Iteration {run_id}/{iterations}:")
        for i, question in enumerate(KEYWORD_QUESTIONS, 1):
            print(f"  [{i}/{len(KEYWORD_QUESTIONS)}] {question[:60]}...", end=" ", flush=True)
            result = run_keyword_query(question, run_id)
            results.append(result)

            if result["status"] == "success":
                print(f"✓ {result['latency_s']}s ({result['data_count']} rows)")
            else:
                print(f"✗ {result['error']}")
        print()

    return results


def run_chat_benchmark(iterations: int) -> list[dict]:
    """Run chat streaming endpoint benchmark."""
    results = []
    total = len(CHAT_QUESTIONS) * iterations

    print(f"\n{'='*80}")
    print(f"CHAT STREAMING ENDPOINT BENCHMARK — {total} queries ({iterations} iterations × {len(CHAT_QUESTIONS)} questions)")
    print(f"{'='*80}\n")

    for run_id in range(1, iterations + 1):
        print(f"Iteration {run_id}/{iterations}:")
        for i, question in enumerate(CHAT_QUESTIONS, 1):
            print(f"  [{i}/{len(CHAT_QUESTIONS)}] {question[:60]}...", end=" ", flush=True)
            result = run_chat_query(question, run_id)
            results.append(result)

            if result["status"] == "success":
                ttft = result['ttft_s'] or 0
                print(f"✓ {result['latency_s']}s (TTFT: {ttft:.2f}s, {result['token_count']} tokens, {result['tools_used']})")
            else:
                print(f"✗ {result['error']}")
        print()

    return results


def save_results(keyword_results: list[dict], chat_results: list[dict], output_dir: str) -> None:
    """Save results to CSV files."""
    os.makedirs(output_dir, exist_ok=True)

    # Keyword results
    keyword_file = os.path.join(output_dir, "keyword_benchmark.csv")
    if keyword_results:
        with open(keyword_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keyword_results[0].keys())
            writer.writeheader()
            writer.writerows(keyword_results)
        print(f"\n✓ Keyword results saved: {keyword_file}")

    # Chat results
    chat_file = os.path.join(output_dir, "chat_benchmark.csv")
    if chat_results:
        with open(chat_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=chat_results[0].keys())
            writer.writeheader()
            writer.writerows(chat_results)
        print(f"✓ Chat results saved: {chat_file}")

    # Summary report
    summary_file = os.path.join(output_dir, "summary.txt")
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("QUERY ENDPOINT BENCHMARK SUMMARY\n")
        f.write("=" * 80 + "\n\n")

        if keyword_results:
            f.write("KEYWORD ENDPOINT:\n")
            success = [r for r in keyword_results if r["status"] == "success"]
            if success:
                latencies = [r["latency_s"] for r in success]
                f.write(f"  Total queries: {len(keyword_results)}\n")
                f.write(f"  Successful: {len(success)} ({len(success)/len(keyword_results)*100:.1f}%)\n")
                f.write(f"  Avg latency: {sum(latencies)/len(latencies):.3f}s\n")
                f.write(f"  Min latency: {min(latencies):.3f}s\n")
                f.write(f"  Max latency: {max(latencies):.3f}s\n")
                f.write(f"  Avg data rows: {sum(r['data_count'] for r in success)/len(success):.1f}\n")
            f.write("\n")

        if chat_results:
            f.write("CHAT STREAMING ENDPOINT:\n")
            success = [r for r in chat_results if r["status"] == "success"]
            if success:
                latencies = [r["latency_s"] for r in success]
                ttfts = [r["ttft_s"] for r in success if r["ttft_s"] is not None]
                tokens = [r["token_count"] for r in success]
                f.write(f"  Total queries: {len(chat_results)}\n")
                f.write(f"  Successful: {len(success)} ({len(success)/len(chat_results)*100:.1f}%)\n")
                f.write(f"  Avg latency: {sum(latencies)/len(latencies):.3f}s\n")
                f.write(f"  Min latency: {min(latencies):.3f}s\n")
                f.write(f"  Max latency: {max(latencies):.3f}s\n")
                if ttfts:
                    f.write(f"  Avg TTFT: {sum(ttfts)/len(ttfts):.3f}s\n")
                    f.write(f"  Min TTFT: {min(ttfts):.3f}s\n")
                    f.write(f"  Max TTFT: {max(ttfts):.3f}s\n")
                f.write(f"  Avg tokens: {sum(tokens)/len(tokens):.1f}\n")
                f.write(f"  Avg tokens/sec: {sum(r['tokens_per_sec'] for r in success)/len(success):.1f}\n")
            f.write("\n")

    print(f"✓ Summary saved: {summary_file}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark query endpoints")
    parser.add_argument("--iterations", type=int, default=3, help="Iterations per question (default: 3)")
    parser.add_argument("--keyword-only", action="store_true", help="Only run keyword endpoint")
    parser.add_argument("--chat-only", action="store_true", help="Only run chat endpoint")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(OUTPUT_DIR, timestamp)

    keyword_results = []
    chat_results = []

    # Note: Keyword endpoint (/api/query) was removed - only chat streaming exists
    if not args.chat_only and False:  # Disabled - keyword endpoint not available
        keyword_results = run_keyword_benchmark(args.iterations)

    if not args.keyword_only:
        chat_results = run_chat_benchmark(args.iterations)

    save_results(keyword_results, chat_results, output_dir)

    print(f"\n{'='*80}")
    print(f"BENCHMARK COMPLETE — Results in {output_dir}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()

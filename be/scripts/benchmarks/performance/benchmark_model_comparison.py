"""Compare analyst chat models: gemini-2.5-flash vs gemini-3-flash-preview.

Instantiates two agents with identical config except the model,
runs the same queries against both, and compares latency + accuracy.

Usage:
    python scripts/benchmark_model_comparison.py
    python scripts/benchmark_model_comparison.py --iterations 2
    python scripts/benchmark_model_comparison.py --quick  # 5 questions only
"""

import argparse
import asyncio
import csv
import json
import os
import time
from datetime import datetime

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy import create_engine

from app.agentic_system.base_agent import AgentConfig, BaseAgent
from app.agentic_system.prompts.analyst_chat import ANALYST_CHAT_PROMPT
from app.agentic_system.tools.sql.schema_builder import (
    build_critical_notes,
    build_schema_description,
)
from app.agentic_system.tools.sql.toolkit import (
    FRAUD_DB_TABLES,
    create_sql_toolkit,
    get_query_tools,
)
from app.config import get_settings

load_dotenv()

MODELS = ["gemini-2.5-flash", "gemini-3-flash-preview"]
OUTPUT_DIR = "outputs/model_comparison"

# Questions covering simple → complex range
FULL_QUESTIONS = [
    # Simple (direct SELECT / COUNT)
    "How many customers are currently blocked?",
    "What is the total amount of blocked withdrawals?",
    "Show me all withdrawals over $5000 with their risk scores",
    # Medium (JOINs, aggregations)
    "Which countries have the highest fraud rate?",
    "Find customers who share the same device fingerprint",
    "What's the average withdrawal amount by decision type?",
    "Show me all VPN users with high risk scores",
    # Complex (CTEs, window functions, self-joins)
    "Find pairs of customers who share the same IP address AND device fingerprint",
    "Show me customers whose total withdrawal amount is in the top 10%",
    "Rank customers by total withdrawal amount and show the top 5",
    # Edge cases
    "Do customers who use VPNs have higher withdrawal amounts on average?",
    "Show me all customers who made withdrawals on February 1st, 2020",
    "Find blocked withdrawals that were approved",
    "What's the correlation between velocity and fraud?",
    "Show me the top 5 highest risk customers",
]

QUICK_QUESTIONS = FULL_QUESTIONS[:5]


def build_agent(model: str, sync_uri: str) -> BaseAgent:
    """Build an analyst agent for the given model."""
    sync_engine = create_engine(sync_uri)
    schema_docs = build_schema_description(sync_engine, FRAUD_DB_TABLES) + build_critical_notes()
    sync_engine.dispose()

    llm = ChatGoogleGenerativeAI(model=model, temperature=0.0)
    toolkit = create_sql_toolkit(sync_uri, llm)
    sql_tools = get_query_tools(toolkit)

    full_prompt = ANALYST_CHAT_PROMPT.replace(
        "## Database Schema (exact columns)", schema_docs
    )

    # gemini-2.5-flash doesn't support thinking_level
    thinking = "low" if "3-flash" in model else None

    config = AgentConfig(
        prompt=full_prompt,
        model=model,
        tools=tuple(sql_tools),
        thinking_level=thinking,
        max_iterations=4,
    )
    return BaseAgent(config)


async def run_query(agent: BaseAgent, question: str) -> dict:
    """Run a single query and capture latency, answer, SQL, and errors."""
    t0 = time.perf_counter()
    sql_queries: list[str] = []
    answer = ""
    error = None

    try:
        result, trace = await agent.invoke_verbose(question)
        answer = str(result)
        for tc in trace:
            if tc["tool"] == "sql_db_query":
                sql_queries.append(tc["args_preview"])
    except Exception as exc:
        error = str(exc)

    elapsed = time.perf_counter() - t0
    return {
        "latency_s": round(elapsed, 3),
        "answer": answer[:2000],
        "sql": "; ".join(sql_queries)[:1000],
        "error": error,
    }


async def benchmark_model(
    model: str, questions: list[str], iterations: int, sync_uri: str,
) -> list[dict]:
    """Run all questions N times for a single model."""
    print(f"\n{'='*80}")
    print(f"  MODEL: {model}")
    print(f"  {len(questions)} questions x {iterations} iterations")
    print(f"{'='*80}\n")

    agent = build_agent(model, sync_uri)

    # Warmup
    print("  Warming up...", end=" ", flush=True)
    try:
        await agent.invoke("How many customers are there?")
        print("done\n")
    except Exception as exc:
        print(f"warmup failed: {exc}\n")

    results = []
    for run_id in range(1, iterations + 1):
        print(f"  Iteration {run_id}/{iterations}:")
        for i, question in enumerate(questions, 1):
            short_q = question[:55]
            print(f"    [{i}/{len(questions)}] {short_q}...", end=" ", flush=True)

            result = await run_query(agent, question)
            result["model"] = model
            result["run_id"] = run_id
            result["question"] = question
            results.append(result)

            if result["error"]:
                print(f"ERR {result['latency_s']}s — {result['error'][:60]}")
            else:
                print(f"OK {result['latency_s']}s ({len(result['answer'])} chars)")

            # Brief pause to avoid rate limits
            await asyncio.sleep(1)
        print()

    return results


def save_results(all_results: list[dict], output_dir: str) -> None:
    """Save per-query CSV + comparison summary."""
    os.makedirs(output_dir, exist_ok=True)

    # --- Raw results CSV ---
    raw_file = os.path.join(output_dir, "raw_results.csv")
    fields = ["model", "run_id", "question", "latency_s", "answer", "sql", "error"]
    with open(raw_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_results)
    print(f"  Raw results: {raw_file}")

    # --- Comparison summary ---
    summary = build_comparison_summary(all_results)
    summary_file = os.path.join(output_dir, "comparison.md")
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"  Comparison:  {summary_file}")

    # --- JSON for programmatic access ---
    json_file = os.path.join(output_dir, "raw_results.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"  JSON:        {json_file}")


def build_comparison_summary(all_results: list[dict]) -> str:
    """Build a markdown comparison report."""
    lines = [
        f"# Model Comparison: Analyst Chat Agent",
        f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    # Per-model aggregate stats
    for model in MODELS:
        model_results = [r for r in all_results if r["model"] == model]
        success = [r for r in model_results if not r["error"]]
        errors = [r for r in model_results if r["error"]]

        if not model_results:
            continue

        latencies = [r["latency_s"] for r in success]
        avg_lat = sum(latencies) / len(latencies) if latencies else 0
        min_lat = min(latencies) if latencies else 0
        max_lat = max(latencies) if latencies else 0
        avg_answer_len = (
            sum(len(r["answer"]) for r in success) / len(success) if success else 0
        )

        lines.append(f"## {model}")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total queries | {len(model_results)} |")
        lines.append(f"| Success | {len(success)} ({len(success)/len(model_results)*100:.0f}%) |")
        lines.append(f"| Errors | {len(errors)} |")
        lines.append(f"| Avg latency | **{avg_lat:.2f}s** |")
        lines.append(f"| Min latency | {min_lat:.2f}s |")
        lines.append(f"| Max latency | {max_lat:.2f}s |")
        lines.append(f"| Avg answer length | {avg_answer_len:.0f} chars |")
        lines.append("")

    # Head-to-head per question
    questions = list(dict.fromkeys(r["question"] for r in all_results))
    lines.append("## Head-to-Head (per question, avg across iterations)")
    lines.append("")
    lines.append("| Question | gemini-2.5-flash | gemini-3-flash | Delta | Winner |")
    lines.append("|----------|-----------------|----------------|-------|--------|")

    model_a, model_b = MODELS[0], MODELS[1]
    a_total, b_total = 0.0, 0.0
    a_count, b_count = 0, 0

    for q in questions:
        a_results = [r for r in all_results if r["question"] == q and r["model"] == model_a and not r["error"]]
        b_results = [r for r in all_results if r["question"] == q and r["model"] == model_b and not r["error"]]

        a_avg = sum(r["latency_s"] for r in a_results) / len(a_results) if a_results else None
        b_avg = sum(r["latency_s"] for r in b_results) / len(b_results) if b_results else None

        if a_avg is not None:
            a_total += a_avg
            a_count += 1
        if b_avg is not None:
            b_total += b_avg
            b_count += 1

        a_str = f"{a_avg:.2f}s" if a_avg else "ERR"
        b_str = f"{b_avg:.2f}s" if b_avg else "ERR"

        if a_avg and b_avg:
            delta = b_avg - a_avg
            delta_str = f"{delta:+.2f}s"
            winner = model_a if a_avg <= b_avg else model_b
        else:
            delta_str = "—"
            winner = "—"

        short_q = q[:50] + ("..." if len(q) > 50 else "")
        lines.append(f"| {short_q} | {a_str} | {b_str} | {delta_str} | {winner} |")

    # Overall winner
    lines.append("")
    a_overall = a_total / a_count if a_count else 0
    b_overall = b_total / b_count if b_count else 0
    lines.append(f"**Overall avg**: {model_a} = {a_overall:.2f}s, {model_b} = {b_overall:.2f}s")

    if a_overall and b_overall:
        if a_overall < b_overall:
            speedup = b_overall / a_overall
            lines.append(f"**Winner**: {model_a} ({speedup:.1f}x faster)")
        else:
            speedup = a_overall / b_overall
            lines.append(f"**Winner**: {model_b} ({speedup:.1f}x faster)")

    # Answer comparison section
    lines.append("")
    lines.append("## Answer Comparison (first iteration)")
    lines.append("")

    for q in questions:
        a_first = next((r for r in all_results if r["question"] == q and r["model"] == model_a and r["run_id"] == 1), None)
        b_first = next((r for r in all_results if r["question"] == q and r["model"] == model_b and r["run_id"] == 1), None)

        short_q = q[:60]
        lines.append(f"### {short_q}")
        lines.append("")

        if a_first:
            answer_preview = a_first["answer"][:300].replace("\n", " ")
            lines.append(f"**{model_a}** ({a_first['latency_s']}s):")
            lines.append(f"> {answer_preview}")
            lines.append("")

        if b_first:
            answer_preview = b_first["answer"][:300].replace("\n", " ")
            lines.append(f"**{model_b}** ({b_first['latency_s']}s):")
            lines.append(f"> {answer_preview}")
            lines.append("")

    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Compare analyst chat models")
    parser.add_argument("--iterations", type=int, default=1, help="Iterations per question (default: 1)")
    parser.add_argument("--quick", action="store_true", help="Only run 5 questions")
    args = parser.parse_args()

    settings = get_settings()
    sync_uri = settings.POSTGRES_URL.replace("+asyncpg", "").split("?")[0]
    questions = QUICK_QUESTIONS if args.quick else FULL_QUESTIONS
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(OUTPUT_DIR, timestamp)

    print(f"\nMODEL COMPARISON BENCHMARK")
    print(f"Models: {' vs '.join(MODELS)}")
    print(f"Questions: {len(questions)}, Iterations: {args.iterations}")
    print(f"Output: {output_dir}")

    all_results = []
    for model in MODELS:
        results = await benchmark_model(model, questions, args.iterations, sync_uri)
        all_results.extend(results)

    print(f"\n{'='*80}")
    print(f"SAVING RESULTS")
    print(f"{'='*80}\n")
    save_results(all_results, output_dir)

    print(f"\n{'='*80}")
    print(f"BENCHMARK COMPLETE — {output_dir}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())

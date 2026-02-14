"""Compare analyst chat temperature settings on gemini-3-flash-preview.

Runs the same representative queries at different temperatures (0.0 → 1.0),
5 iterations each, to measure effect on latency, answer consistency, and quality.

Usage:
    python -m scripts.benchmark_temperature
    python -m scripts.benchmark_temperature --iterations 3
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

MODEL = "gemini-3-flash-preview"
TEMPERATURES = [0.0, 0.2, 0.5, 0.8, 1.0]
OUTPUT_DIR = "outputs/temperature_comparison"

# Representative sample: 1 simple, 2 medium, 1 complex, 1 edge case
QUESTIONS = [
    {"q": "How many customers are currently blocked?", "type": "simple"},
    {"q": "Which countries have the highest fraud rate?", "type": "medium"},
    {"q": "Find customers who share the same device fingerprint", "type": "medium"},
    {"q": "Do customers who use VPNs have higher withdrawal amounts on average?", "type": "complex"},
    {"q": "Find blocked withdrawals that were approved", "type": "edge_case"},
]


def build_agent(temperature: float, sync_uri: str) -> BaseAgent:
    """Build analyst agent at a specific temperature."""
    sync_engine = create_engine(sync_uri)
    schema_docs = (
        build_schema_description(sync_engine, FRAUD_DB_TABLES)
        + build_critical_notes()
    )
    sync_engine.dispose()

    llm = ChatGoogleGenerativeAI(model=MODEL, temperature=temperature)
    toolkit = create_sql_toolkit(sync_uri, llm)
    sql_tools = get_query_tools(toolkit)

    full_prompt = ANALYST_CHAT_PROMPT.replace(
        "## Database Schema (exact columns)", schema_docs
    )

    config = AgentConfig(
        prompt=full_prompt,
        model=MODEL,
        tools=tuple(sql_tools),
        thinking_level="low",
        max_iterations=4,
    )
    return BaseAgent(config)


async def run_query(agent: BaseAgent, question: str) -> dict:
    """Run a single query, capture latency + answer + SQL."""
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


async def benchmark_temperature(
    temperature: float, iterations: int, sync_uri: str,
) -> list[dict]:
    """Run all questions N times at a given temperature."""
    print(f"\n{'='*70}")
    print(f"  TEMPERATURE: {temperature}")
    print(f"  {len(QUESTIONS)} questions x {iterations} iterations")
    print(f"{'='*70}\n")

    agent = build_agent(temperature, sync_uri)

    # Warmup
    print("  Warming up...", end=" ", flush=True)
    try:
        await agent.invoke("How many customers are there?")
        print("done\n")
    except Exception as exc:
        print(f"failed: {exc}\n")

    results = []
    for run_id in range(1, iterations + 1):
        print(f"  Run {run_id}/{iterations}:")
        for i, item in enumerate(QUESTIONS, 1):
            q = item["q"]
            short_q = q[:50]
            print(f"    [{i}/{len(QUESTIONS)}] {short_q}...", end=" ", flush=True)

            result = await run_query(agent, q)
            result["temperature"] = temperature
            result["run_id"] = run_id
            result["question"] = q
            result["query_type"] = item["type"]
            results.append(result)

            status = "ERR" if result["error"] else "OK"
            print(f"{status} {result['latency_s']}s")

            await asyncio.sleep(1)
        print()

    return results


def compute_consistency(results: list[dict], question: str, temp: float) -> float:
    """Score answer consistency 0-1 across iterations for a question+temp."""
    answers = [
        r["answer"] for r in results
        if r["question"] == question
        and r["temperature"] == temp
        and not r["error"]
    ]
    if len(answers) < 2:
        return 1.0

    # Compare each pair: ratio of shared words
    scores = []
    for i in range(len(answers)):
        for j in range(i + 1, len(answers)):
            words_a = set(answers[i].lower().split())
            words_b = set(answers[j].lower().split())
            union = words_a | words_b
            if not union:
                scores.append(1.0)
                continue
            overlap = len(words_a & words_b) / len(union)
            scores.append(overlap)
    return round(sum(scores) / len(scores), 3) if scores else 1.0


def save_results(all_results: list[dict], output_dir: str) -> None:
    """Save raw CSV + comparison markdown."""
    os.makedirs(output_dir, exist_ok=True)

    # Raw CSV
    raw_file = os.path.join(output_dir, "raw_results.csv")
    fields = [
        "temperature", "run_id", "question", "query_type",
        "latency_s", "answer", "sql", "error",
    ]
    with open(raw_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_results)
    print(f"  Raw CSV:    {raw_file}")

    # JSON
    json_file = os.path.join(output_dir, "raw_results.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"  JSON:       {json_file}")

    # Comparison report
    report = build_report(all_results)
    report_file = os.path.join(output_dir, "comparison.md")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  Report:     {report_file}")


def build_report(all_results: list[dict]) -> str:
    """Build markdown analysis report."""
    lines = [
        "# Temperature Comparison: Analyst Chat Agent",
        f"**Model**: {MODEL}",
        f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Temperatures**: {', '.join(str(t) for t in TEMPERATURES)}",
        "",
        "## Aggregate Stats",
        "",
        "| Temp | Avg Latency | Min | Max | Std Dev | Success | Avg Answer Len |",
        "|------|------------|-----|-----|---------|---------|----------------|",
    ]

    for temp in TEMPERATURES:
        rows = [r for r in all_results if r["temperature"] == temp]
        success = [r for r in rows if not r["error"]]
        if not success:
            lines.append(f"| {temp} | — | — | — | — | 0/{len(rows)} | — |")
            continue

        lats = [r["latency_s"] for r in success]
        avg_lat = sum(lats) / len(lats)
        min_lat = min(lats)
        max_lat = max(lats)
        mean = avg_lat
        std_dev = (sum((x - mean) ** 2 for x in lats) / len(lats)) ** 0.5
        avg_len = sum(len(r["answer"]) for r in success) / len(success)

        lines.append(
            f"| {temp} | **{avg_lat:.2f}s** | {min_lat:.2f}s | {max_lat:.2f}s "
            f"| {std_dev:.2f}s | {len(success)}/{len(rows)} | {avg_len:.0f} |"
        )

    # Per-question breakdown
    lines.extend(["", "## Per-Question Latency (avg across iterations)", ""])
    header = "| Question | Type |"
    sep = "|----------|------|"
    for t in TEMPERATURES:
        header += f" T={t} |"
        sep += "------|"
    lines.append(header)
    lines.append(sep)

    for item in QUESTIONS:
        q = item["q"]
        short_q = q[:45] + ("..." if len(q) > 45 else "")
        row = f"| {short_q} | {item['type']} |"
        for temp in TEMPERATURES:
            hits = [
                r["latency_s"] for r in all_results
                if r["question"] == q and r["temperature"] == temp and not r["error"]
            ]
            if hits:
                avg = sum(hits) / len(hits)
                row += f" {avg:.2f}s |"
            else:
                row += " ERR |"
        lines.append(row)

    # Consistency analysis
    lines.extend(["", "## Answer Consistency (word overlap across iterations)", ""])
    header = "| Question |"
    sep = "|----------|"
    for t in TEMPERATURES:
        header += f" T={t} |"
        sep += "------|"
    lines.append(header)
    lines.append(sep)

    for item in QUESTIONS:
        q = item["q"]
        short_q = q[:45] + ("..." if len(q) > 45 else "")
        row = f"| {short_q} |"
        for temp in TEMPERATURES:
            score = compute_consistency(all_results, q, temp)
            row += f" {score:.0%} |"
        lines.append(row)

    # Answer samples at each temp (first iteration only)
    lines.extend(["", "## Answer Samples (first iteration)", ""])

    for item in QUESTIONS:
        q = item["q"]
        short_q = q[:60]
        lines.append(f"### {short_q}")
        lines.append("")

        for temp in TEMPERATURES:
            first = next(
                (r for r in all_results
                 if r["question"] == q and r["temperature"] == temp and r["run_id"] == 1),
                None,
            )
            if not first or first["error"]:
                lines.append(f"**T={temp}**: ERROR")
            else:
                preview = first["answer"][:250].replace("\n", " ")
                lines.append(f"**T={temp}** ({first['latency_s']}s):")
                lines.append(f"> {preview}")
            lines.append("")

    # Recommendation
    lines.extend(["", "## Analysis", ""])
    lines.append("Key metrics to evaluate:")
    lines.append("- **Latency**: Does higher temperature increase response time?")
    lines.append("- **Consistency**: Do answers vary significantly across runs?")
    lines.append("- **Accuracy**: Do higher temps cause SQL hallucinations or wrong data?")
    lines.append("- **Naturalness**: Do higher temps produce more readable answers?")

    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark temperature effect")
    parser.add_argument(
        "--iterations", type=int, default=5,
        help="Iterations per question per temperature (default: 5)",
    )
    args = parser.parse_args()

    settings = get_settings()
    sync_uri = settings.POSTGRES_URL.replace("+asyncpg", "").split("?")[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(OUTPUT_DIR, timestamp)

    total = len(TEMPERATURES) * len(QUESTIONS) * args.iterations
    print(f"\nTEMPERATURE COMPARISON BENCHMARK")
    print(f"Model: {MODEL}")
    print(f"Temperatures: {TEMPERATURES}")
    print(f"Questions: {len(QUESTIONS)}, Iterations: {args.iterations}")
    print(f"Total queries: {total}")
    print(f"Output: {output_dir}")

    all_results = []
    for temp in TEMPERATURES:
        results = await benchmark_temperature(temp, args.iterations, sync_uri)
        all_results.extend(results)

    print(f"\n{'='*70}")
    print(f"SAVING RESULTS")
    print(f"{'='*70}\n")
    save_results(all_results, output_dir)

    print(f"\n{'='*70}")
    print(f"BENCHMARK COMPLETE — {output_dir}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())

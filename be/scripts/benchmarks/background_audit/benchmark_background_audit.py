"""Benchmark the Stage 2 background audit pipeline.

Tests:
  1. Trigger a run via POST /background-audits/trigger
  2. Connect to SSE stream and collect all events
  3. Validate event types, ordering, and content
  4. Check artifacts on disk
  5. Performance timing per phase
  6. Multiple iterations with CSV output

Usage:
  python scripts/benchmark_background_audit.py
  python scripts/benchmark_background_audit.py --iterations 3
  python scripts/benchmark_background_audit.py --base-url http://localhost:8080/api
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASE_URL = "http://localhost:18080/api"
OUTPUT_DIR = "outputs/background_audit_benchmark"
ARTIFACT_BASE = "outputs/background_audits/stage_1"

EXPECTED_EVENT_TYPES = {
    "phase_start", "progress", "hypothesis", "candidate",
    "agent_tool", "complete", "error",
}
EXPECTED_PHASES = {"extract", "embed_cluster", "investigate", "artifacts"}
REQUIRED_ARTIFACTS = [
    "run_summary.json",
    "timings.json",
    "clusters.json",
    "candidates.json",
    "embedding_metrics.json",
    "audit_report.md",
    "artifact_manifest.json",
    "agent_observability/admin_brief.md",
    "agent_observability/tool_trace.json",
    "agent_observability/clustering_comparison.json",
]


def trigger_run(client: httpx.Client, base: str) -> str:
    """Trigger a background audit run. Returns run_id."""
    resp = client.post(
        f"{base}/background-audits/trigger",
        json={"lookback_days": 30, "run_mode": "full"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["run_id"]


def collect_sse_events(base: str, run_id: str) -> list[dict]:
    """Connect to SSE stream and collect all events until complete/error/timeout."""
    events: list[dict] = []
    url = f"{base}/background-audits/runs/{run_id}/stream"

    with httpx.stream("GET", url, timeout=180.0) as stream:
        buffer = ""
        for chunk in stream.iter_text():
            buffer += chunk
            while "\n\n" in buffer:
                raw, buffer = buffer.split("\n\n", 1)
                event = _parse_sse(raw)
                if event:
                    events.append(event)
                    _print_event(event)
                    if event.get("type") in ("complete", "error"):
                        return events
    return events


def _parse_sse(raw: str) -> dict | None:
    """Parse a raw SSE frame into a dict."""
    event_type = None
    data_str = None
    for line in raw.strip().split("\n"):
        if line.startswith("event: "):
            event_type = line[7:].strip()
        elif line.startswith("data: "):
            data_str = line[6:].strip()
        elif line.startswith(":"):
            return None  # keepalive comment
    if data_str:
        try:
            parsed = json.loads(data_str)
            parsed["_event_type"] = event_type
            return parsed
        except json.JSONDecodeError:
            return {"_raw": data_str, "_event_type": event_type}
    return None


def _print_event(event: dict) -> None:
    etype = event.get("type", event.get("_event_type", "?")) or "?"
    title = event.get("title", "") or ""
    detail = event.get("detail", "") or ""
    phase = event.get("phase", "") or ""
    progress = event.get("progress")
    prog_str = f" [{progress:.0%}]" if progress is not None else ""
    print(f"  [{etype:<12}] {phase:<14} {title}{prog_str}  {detail}")


def validate_events(events: list[dict]) -> dict:
    """Validate SSE events and return a check summary."""
    checks: dict[str, bool] = {}
    types_seen = {e.get("type", e.get("_event_type")) for e in events}

    checks["has_phase_start"] = "phase_start" in types_seen
    checks["has_progress"] = "progress" in types_seen
    checks["has_complete_or_error"] = bool(types_seen & {"complete", "error"})
    checks["no_unknown_types"] = types_seen <= EXPECTED_EVENT_TYPES | {None}

    # Check phase ordering
    phases_seen = [e.get("phase") for e in events if e.get("type") == "phase_start"]
    checks["extract_phase_first"] = phases_seen[0] == "extract" if phases_seen else False
    checks["all_phases_present"] = set(phases_seen) >= {"extract", "embed_cluster"}

    # Hypothesis events
    hypothesis_events = [e for e in events if e.get("type") == "hypothesis"]
    checks["has_hypothesis_events"] = len(hypothesis_events) > 0
    checks["hypothesis_has_cluster_id"] = all(
        "cluster_id" in e.get("metadata", {}) for e in hypothesis_events
    )

    # Candidate events
    candidate_events = [e for e in events if e.get("type") == "candidate"]
    checks["has_candidate_events"] = len(candidate_events) > 0

    # Agent tool events
    tool_events = [e for e in events if e.get("type") == "agent_tool"]
    checks["has_agent_tool_events"] = len(tool_events) > 0

    # Terminal event is last
    if events:
        last_type = events[-1].get("type", events[-1].get("_event_type"))
        checks["terminal_event_last"] = last_type in ("complete", "error")

    return checks


def validate_artifacts(run_id: str) -> dict:
    """Check that all expected artifacts exist and have valid content."""
    checks: dict[str, bool] = {}
    base = Path(ARTIFACT_BASE) / run_id

    checks["artifact_dir_exists"] = base.exists()
    if not base.exists():
        return checks

    for artifact in REQUIRED_ARTIFACTS:
        path = base / artifact
        key = f"artifact_{artifact.replace('/', '_').replace('.', '_')}"
        checks[key] = path.exists() and path.stat().st_size > 0

    # Validate candidates.json has enriched fields
    candidates_path = base / "candidates.json"
    if candidates_path.exists():
        data = json.loads(candidates_path.read_text())
        if data:
            first = data[0]
            checks["candidates_has_formal_pattern"] = "formal_pattern_name" in first
            checks["candidates_has_sql_findings"] = "sql_findings" in first
            checks["candidates_has_web_references"] = "web_references" in first

    # Validate tool_trace.json
    trace_path = base / "agent_observability" / "tool_trace.json"
    if trace_path.exists():
        trace_data = json.loads(trace_path.read_text())
        checks["tool_trace_not_empty"] = len(trace_data) > 0

    # Validate admin_brief.md has Stage 2 sections
    brief_path = base / "agent_observability" / "admin_brief.md"
    if brief_path.exists():
        brief = brief_path.read_text()
        checks["brief_has_sql_findings"] = "SQL Findings" in brief or "Candidate Patterns" in brief
        checks["brief_is_stage_2"] = "Stage 2" in brief

    # Validate clusters.json has clustering_method
    clusters_path = base / "clusters.json"
    if clusters_path.exists():
        clusters = json.loads(clusters_path.read_text())
        if clusters:
            checks["clusters_has_method"] = "clustering_method" in clusters[0]

    return checks


def check_run_status(client: httpx.Client, base: str, run_id: str) -> dict:
    """Poll run status after completion."""
    resp = client.get(f"{base}/background-audits/runs/{run_id}", timeout=10)
    if resp.status_code == 200:
        return resp.json()
    return {"error": resp.status_code}


def extract_timings(events: list[dict]) -> dict[str, float]:
    """Extract phase timings from SSE events."""
    timings: dict[str, float] = {}
    phase_starts: dict[str, str] = {}

    for e in events:
        etype = e.get("type")
        phase = e.get("phase")
        ts = e.get("timestamp", "")

        if etype == "phase_start" and phase:
            phase_starts[phase] = ts
        elif etype == "progress" and phase and phase in phase_starts:
            try:
                start = datetime.fromisoformat(phase_starts[phase])
                end = datetime.fromisoformat(ts)
                timings[phase] = (end - start).total_seconds()
            except (ValueError, TypeError):
                pass
    return timings


def run_single(client: httpx.Client, base: str, iteration: int) -> dict:
    """Run a single benchmark iteration. Returns row dict."""
    print(f"\n{'='*60}")
    print(f"  Iteration {iteration}")
    print(f"{'='*60}")

    t0 = time.perf_counter()
    run_id = trigger_run(client, base)
    trigger_ms = round((time.perf_counter() - t0) * 1000, 1)
    print(f"  Triggered: {run_id} ({trigger_ms}ms)")

    print(f"\n  SSE Events:")
    t_stream = time.perf_counter()
    events = collect_sse_events(base, run_id)
    stream_s = round(time.perf_counter() - t_stream, 2)

    event_checks = validate_events(events)
    artifact_checks = validate_artifacts(run_id)
    sse_timings = extract_timings(events)
    status = check_run_status(client, base, run_id)

    # Count events by type
    type_counts: dict[str, int] = {}
    for e in events:
        t = e.get("type", e.get("_event_type", "unknown"))
        type_counts[t] = type_counts.get(t, 0) + 1

    total_s = round(time.perf_counter() - t0, 2)

    # Print summary
    event_pass = sum(1 for v in event_checks.values() if v)
    event_total = len(event_checks)
    artifact_pass = sum(1 for v in artifact_checks.values() if v)
    artifact_total = len(artifact_checks)

    print(f"\n  Results:")
    print(f"    Total time:     {total_s}s")
    print(f"    SSE stream:     {stream_s}s ({len(events)} events)")
    print(f"    Event types:    {type_counts}")
    print(f"    Event checks:   {event_pass}/{event_total} passed")
    print(f"    Artifact checks: {artifact_pass}/{artifact_total} passed")
    print(f"    Run status:     {status.get('status', 'unknown')}")

    if sse_timings:
        print(f"    Phase timings:  {sse_timings}")

    # Print failures
    for name, passed in {**event_checks, **artifact_checks}.items():
        if not passed:
            print(f"    FAIL: {name}")

    return {
        "iteration": iteration,
        "run_id": run_id,
        "status": status.get("status", "unknown"),
        "total_s": total_s,
        "trigger_ms": trigger_ms,
        "stream_s": stream_s,
        "event_count": len(events),
        "hypothesis_count": type_counts.get("hypothesis", 0),
        "candidate_count": type_counts.get("candidate", 0),
        "agent_tool_count": type_counts.get("agent_tool", 0),
        "extract_s": sse_timings.get("extract", 0),
        "embed_cluster_s": sse_timings.get("embed_cluster", 0),
        "investigate_s": sse_timings.get("investigate", 0),
        "event_checks_passed": event_pass,
        "event_checks_total": event_total,
        "artifact_checks_passed": artifact_pass,
        "artifact_checks_total": artifact_total,
        "counters": json.dumps(status.get("counters", {})),
    }


def print_summary(rows: list[dict]) -> None:
    """Print aggregate summary."""
    n = len(rows)
    print(f"\n{'='*60}")
    print(f"  BACKGROUND AUDIT BENCHMARK — {n} iterations")
    print(f"{'='*60}")

    totals = [r["total_s"] for r in rows]
    streams = [r["stream_s"] for r in rows]
    events = [r["event_count"] for r in rows]
    hypotheses = [r["hypothesis_count"] for r in rows]
    candidates = [r["candidate_count"] for r in rows]
    tools = [r["agent_tool_count"] for r in rows]

    avg = lambda xs: sum(xs) / len(xs) if xs else 0

    print(f"\n  Timing:")
    print(f"    Total:       avg={avg(totals):.1f}s  min={min(totals):.1f}s  max={max(totals):.1f}s")
    print(f"    SSE stream:  avg={avg(streams):.1f}s")

    print(f"\n  Events:")
    print(f"    Total:       avg={avg(events):.0f}")
    print(f"    Hypotheses:  avg={avg(hypotheses):.1f}")
    print(f"    Candidates:  avg={avg(candidates):.1f}")
    print(f"    Tool calls:  avg={avg(tools):.1f}")

    all_event_ok = all(r["event_checks_passed"] == r["event_checks_total"] for r in rows)
    all_artifact_ok = all(r["artifact_checks_passed"] == r["artifact_checks_total"] for r in rows)
    all_completed = all(r["status"] == "completed" for r in rows)

    print(f"\n  Validation:")
    print(f"    All runs completed: {'PASS' if all_completed else 'FAIL'}")
    print(f"    All event checks:   {'PASS' if all_event_ok else 'FAIL'}")
    print(f"    All artifact checks: {'PASS' if all_artifact_ok else 'FAIL'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark background audit pipeline")
    parser.add_argument("--iterations", "-n", type=int, default=1)
    parser.add_argument("--base-url", type=str, default=BASE_URL)
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(OUTPUT_DIR, timestamp)
    os.makedirs(out_dir, exist_ok=True)

    client = httpx.Client()
    rows: list[dict] = []

    for i in range(1, args.iterations + 1):
        row = run_single(client, args.base_url, i)
        rows.append(row)

    client.close()

    # Save CSV
    csv_path = os.path.join(out_dir, "background_audit_benchmark.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    # Save JSON with full detail
    json_path = os.path.join(out_dir, "background_audit_benchmark.json")
    with open(json_path, "w") as f:
        json.dump({
            "run_at": datetime.now(timezone.utc).isoformat(),
            "iterations": args.iterations,
            "base_url": args.base_url,
            "results": rows,
        }, f, indent=2)

    print_summary(rows)
    print(f"\n  CSV saved:  {csv_path}")
    print(f"  JSON saved: {json_path}")


if __name__ == "__main__":
    main()

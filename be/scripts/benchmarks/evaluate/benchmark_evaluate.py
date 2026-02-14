"""Benchmark /api/payout/evaluate and export structured CSV outputs."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import os
import re
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor


DEFAULT_CUSTOMERS = ["CUST-001", "CUST-007", "CUST-011"]
EXPECTED_DECISIONS = {
    "CUST-001": "approved",
    "CUST-007": "escalated",
    "CUST-011": "blocked",
}
RATE_LIMIT_TOKENS = (
    "429",
    "rate limit",
    "too many requests",
    "resource_exhausted",
    "quota",
)
GEMINI_MODEL = "gemini-2.5-flash"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * (p / 100.0)
    low = math.floor(k)
    high = math.ceil(k)
    if low == high:
        return ordered[int(k)]
    return ordered[low] + (ordered[high] - ordered[low]) * (k - low)


def default_db_dsn() -> str:
    password = os.getenv("POSTGRES_PASSWORD", "changeme")
    return f"postgresql://user:{password}@localhost:15432/fraud_detection"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:18080")
    parser.add_argument("--endpoint", default="/api/payout/evaluate")
    parser.add_argument("--db-dsn", default=os.getenv("BENCHMARK_DB_DSN", default_db_dsn()))
    parser.add_argument("--customer-ids", default=",".join(DEFAULT_CUSTOMERS))
    parser.add_argument("--fallback-sample-size", type=int, default=3)
    parser.add_argument("--iterations", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument(
        "--run-llm-comparison",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--output-dir", default="outputs/performance_benchmark")
    parser.add_argument("--docker-log-container", default="deriv_app")
    parser.add_argument("--skip-docker-log-scan", action="store_true")
    parser.add_argument("--healthcheck-path", default="/api/health")
    parser.add_argument("--healthcheck-timeout-s", type=float, default=20.0)
    parser.add_argument("--skip-healthcheck", action="store_true")
    return parser.parse_args()


def compact_text(text: str, limit: int = 180) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def build_llm_concise_rows(
    run_id: str,
    request_rows: list[dict[str, Any]],
    indicator_rows: list[dict[str, Any]],
    summary: dict[str, Any],
) -> list[dict[str, Any]]:
    indicator_by_request: dict[int, list[dict[str, Any]]] = {}
    for row in indicator_rows:
        req_id = int(row.get("request_id", 0))
        indicator_by_request.setdefault(req_id, []).append(row)

    concise_rows: list[dict[str, Any]] = []
    for row in request_rows:
        req_id = int(row["request_id"])
        indicators = indicator_by_request.get(req_id, [])
        reasoning_summary = " || ".join(
            f"{i.get('indicator_name', 'unknown')}: {compact_text(str(i.get('indicator_reasoning', '')), 110)}"
            for i in indicators
        )
        concise_rows.append(
            {
                "run_id": run_id,
                "row_type": "request",
                "request_id": row["request_id"],
                "iteration": row["iteration"],
                "customer_id": row["customer_id"],
                "withdrawal_id": row["withdrawal_id"],
                "model": GEMINI_MODEL,
                "http_status": row["http_status"],
                "request_ok": row["request_ok"],
                "client_elapsed_ms": row["client_elapsed_ms"],
                "server_elapsed_s": row["server_elapsed_s"],
                "llm_comparison_elapsed_s": row["llm_comparison_elapsed_s"],
                "llm_comparison_indicator_count": row["llm_comparison_indicator_count"],
                "llm_comparison_score": row["llm_comparison_score"],
                "llm_comparison_decision": row["llm_comparison_decision"],
                "gray_zone_used": row["gray_zone_used"],
                "gray_zone_elapsed_s": row["gray_zone_elapsed_s"],
                "decision": row["decision"],
                "rate_limited_http_429": row["rate_limited_http_429"],
                "rate_limited_signal": row["rate_limited_signal"],
                "rate_limited_reason": row["rate_limited_reason"],
                "gray_zone_reasoning": compact_text(str(row.get("gray_zone_reasoning", "")), 220),
                "llm_indicator_reasoning": compact_text(reasoning_summary, 700),
                "error": row["error"],
            }
        )

    concise_rows.append(
        {
            "run_id": run_id,
            "row_type": "aggregate",
            "request_id": "",
            "iteration": "",
            "customer_id": "ALL",
            "withdrawal_id": "",
            "model": GEMINI_MODEL,
            "http_status": "",
            "request_ok": summary["ok_requests"],
            "client_elapsed_ms": summary["client_ms_avg"],
            "server_elapsed_s": summary["server_elapsed_s_avg"],
            "llm_comparison_elapsed_s": "",
            "llm_comparison_indicator_count": "",
            "llm_comparison_score": "",
            "llm_comparison_decision": str(summary["decision_counts"]),
            "gray_zone_used": "",
            "gray_zone_elapsed_s": "",
            "decision": "",
            "rate_limited_http_429": summary["rate_limited_http_429_count"],
            "rate_limited_signal": summary["rate_limited_signal_count"],
            "rate_limited_reason": "",
            "gray_zone_reasoning": "",
            "llm_indicator_reasoning": (
                f"p50={summary['client_ms_p50']}ms; p95={summary['client_ms_p95']}ms; "
                f"errors={summary['error_requests']}"
            ),
            "error": summary.get("docker_log_error", ""),
        }
    )
    return concise_rows


async def wait_for_api_ready(base_url: str, path: str, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    url = f"{base_url.rstrip('/')}{path}"
    last_error = ""

    async with httpx.AsyncClient(timeout=httpx.Timeout(3.0)) as client:
        while time.monotonic() < deadline:
            try:
                resp = await client.get(url)
                if 200 <= resp.status_code < 500:
                    return
                last_error = f"status={resp.status_code}"
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
            await asyncio.sleep(0.5)

    raise RuntimeError(
        f"API health check failed within {timeout_s:.1f}s at {url}. Last error: {last_error}"
    )


def get_targets(db_dsn: str, customer_ids: list[str], fallback_sample_size: int) -> tuple[list[dict[str, Any]], list[str]]:
    base_sql = """
        SELECT
            w.id::text AS withdrawal_id,
            c.external_id AS customer_id,
            w.amount::double precision AS amount,
            w.recipient_name,
            w.recipient_account,
            w.ip_address,
            w.device_fingerprint,
            c.country AS customer_country,
            w.status,
            w.requested_at
        FROM withdrawals w
        JOIN customers c ON c.id = w.customer_id
    """

    with psycopg2.connect(db_dsn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            missing: list[str] = []
            selected: list[dict[str, Any]] = []

            if customer_ids:
                cur.execute(
                    base_sql
                    + " WHERE c.external_id = ANY(%s) ORDER BY w.requested_at DESC",
                    (customer_ids,),
                )
                rows = cur.fetchall()
                latest_by_customer: dict[str, dict[str, Any]] = {}
                for row in rows:
                    cid = row["customer_id"]
                    if cid not in latest_by_customer:
                        latest_by_customer[cid] = dict(row)

                for cid in customer_ids:
                    if cid in latest_by_customer:
                        selected.append(latest_by_customer[cid])
                    else:
                        missing.append(cid)

            if not selected:
                cur.execute(
                    base_sql
                    + " WHERE w.status = 'pending' ORDER BY w.requested_at DESC LIMIT %s",
                    (fallback_sample_size,),
                )
                selected = [dict(r) for r in cur.fetchall()]

    return selected, missing


def rate_limit_signal(status_code: int, payload: dict[str, Any], raw_text: str) -> tuple[bool, str]:
    if status_code == 429:
        return True, "http_429"

    blobs = [raw_text]
    gray_zone = payload.get("gray_zone")
    if isinstance(gray_zone, dict):
        blobs.append(str(gray_zone.get("reasoning", "")))
    blobs.append(json.dumps(payload, ensure_ascii=False))

    merged = " ".join(blobs).lower()
    for token in RATE_LIMIT_TOKENS:
        if token in merged:
            return True, f"token:{token}"
    return False, ""


async def run_requests(
    args: argparse.Namespace,
    targets: list[dict[str, Any]],
    run_started_at: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str]:
    url = f"{args.base_url.rstrip('/')}{args.endpoint}"
    workload: list[tuple[int, dict[str, Any]]] = []
    for i in range(1, args.iterations + 1):
        for target in targets:
            workload.append((i, target))

    semaphore = asyncio.Semaphore(args.concurrency)
    timeout = httpx.Timeout(args.timeout_s)

    async with httpx.AsyncClient(timeout=timeout) as client:
        async def one_request(seq_id: int, iteration: int, target: dict[str, Any]) -> dict[str, Any]:
            payload = {
                "withdrawal_id": target["withdrawal_id"],
                "customer_id": target["customer_id"],
                "amount": float(target["amount"]),
                "recipient_name": target["recipient_name"],
                "recipient_account": target["recipient_account"],
                "ip_address": target["ip_address"],
                "device_fingerprint": target["device_fingerprint"],
                "customer_country": target["customer_country"],
                "run_llm_comparison": bool(args.run_llm_comparison),
            }

            started = utc_now()
            t0 = time.perf_counter()

            async with semaphore:
                try:
                    resp = await client.post(url, json=payload)
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0

                    response_payload: dict[str, Any]
                    try:
                        response_payload = resp.json()
                    except Exception:
                        response_payload = {}

                    raw_text = resp.text[:4000]
                    rl_signal, rl_reason = rate_limit_signal(resp.status_code, response_payload, raw_text)
                    decision = str(response_payload.get("decision", ""))
                    expected = EXPECTED_DECISIONS.get(target["customer_id"], "")

                    llm_comp = response_payload.get("llm_comparison")
                    llm_elapsed = ""
                    llm_count = 0
                    llm_score = ""
                    llm_decision = ""
                    if isinstance(llm_comp, dict):
                        llm_elapsed = llm_comp.get("elapsed_s", "")
                        llm_count = len(llm_comp.get("indicators", []))
                        llm_score = llm_comp.get("score", "")
                        llm_decision = llm_comp.get("decision", "")

                    gray_zone = response_payload.get("gray_zone")
                    gray_zone_used = isinstance(gray_zone, dict)
                    gray_zone_elapsed = gray_zone.get("elapsed_s", "") if gray_zone_used else ""
                    gray_zone_reasoning = str(gray_zone.get("reasoning", "")) if gray_zone_used else ""

                    llm_avg_indicator_elapsed = ""
                    if isinstance(llm_elapsed, (float, int)) and llm_count > 0:
                        llm_avg_indicator_elapsed = round(float(llm_elapsed) / float(llm_count), 4)

                    request_row = {
                        "request_id": seq_id,
                        "iteration": iteration,
                        "started_at": utc_iso(started),
                        "withdrawal_id": target["withdrawal_id"],
                        "customer_id": target["customer_id"],
                        "expected_decision": expected,
                        "decision_matches_expected": bool(expected and decision == expected),
                        "amount": float(target["amount"]),
                        "http_status": resp.status_code,
                        "request_ok": resp.status_code < 400,
                        "client_elapsed_ms": round(elapsed_ms, 2),
                        "server_elapsed_s": response_payload.get("elapsed_s", ""),
                        "decision": decision,
                        "risk_score": response_payload.get("risk_score", ""),
                        "risk_percent": response_payload.get("risk_percent", ""),
                        "risk_level": response_payload.get("risk_level", ""),
                        "gray_zone_used": gray_zone_used,
                        "gray_zone_decision": gray_zone.get("decision", "") if gray_zone_used else "",
                        "gray_zone_elapsed_s": gray_zone_elapsed,
                        "gray_zone_reasoning": gray_zone_reasoning,
                        "llm_comparison_enabled": bool(args.run_llm_comparison),
                        "llm_comparison_elapsed_s": llm_elapsed,
                        "llm_comparison_indicator_count": llm_count,
                        "llm_comparison_score": llm_score,
                        "llm_comparison_decision": llm_decision,
                        "rate_limited_http_429": resp.status_code == 429,
                        "rate_limited_signal": rl_signal,
                        "rate_limited_reason": rl_reason,
                        "error": "",
                        "response_excerpt": raw_text.replace("\n", " ")[:1000],
                    }

                    gemini_row = {
                        "request_id": seq_id,
                        "iteration": iteration,
                        "started_at": utc_iso(started),
                        "customer_id": target["customer_id"],
                        "withdrawal_id": target["withdrawal_id"],
                        "model": GEMINI_MODEL,
                        "http_status": resp.status_code,
                        "request_ok": resp.status_code < 400,
                        "client_elapsed_ms": round(elapsed_ms, 2),
                        "server_elapsed_s": response_payload.get("elapsed_s", ""),
                        "decision": decision,
                        "gray_zone_used": gray_zone_used,
                        "gray_zone_decision": gray_zone.get("decision", "") if gray_zone_used else "",
                        "gray_zone_elapsed_s": gray_zone_elapsed,
                        "gray_zone_reasoning": gray_zone_reasoning,
                        "llm_comparison_enabled": bool(args.run_llm_comparison),
                        "llm_comparison_elapsed_s": llm_elapsed,
                        "llm_comparison_indicator_count": llm_count,
                        "llm_avg_indicator_elapsed_s": llm_avg_indicator_elapsed,
                        "llm_comparison_score": llm_score,
                        "llm_comparison_decision": llm_decision,
                        "rate_limited_http_429": resp.status_code == 429,
                        "rate_limited_signal": rl_signal,
                        "rate_limited_reason": rl_reason,
                        "error": "",
                    }

                    indicator_rows: list[dict[str, Any]] = []
                    if isinstance(llm_comp, dict):
                        for ind in llm_comp.get("indicators", []):
                            if not isinstance(ind, dict):
                                continue
                            indicator_rows.append(
                                {
                                    "request_id": seq_id,
                                    "iteration": iteration,
                                    "customer_id": target["customer_id"],
                                    "withdrawal_id": target["withdrawal_id"],
                                    "model": GEMINI_MODEL,
                                    "indicator_name": ind.get("name", ""),
                                    "indicator_display_name": ind.get("display_name", ""),
                                    "indicator_score": ind.get("score", ""),
                                    "indicator_confidence": ind.get("confidence", ""),
                                    "indicator_reasoning": str(ind.get("reasoning", "")),
                                    "indicator_evidence": json.dumps(ind.get("evidence", {}), ensure_ascii=False),
                                }
                            )

                    return {
                        "request_row": request_row,
                        "gemini_row": gemini_row,
                        "indicator_rows": indicator_rows,
                    }
                except Exception as exc:
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    request_row = {
                        "request_id": seq_id,
                        "iteration": iteration,
                        "started_at": utc_iso(started),
                        "withdrawal_id": target["withdrawal_id"],
                        "customer_id": target["customer_id"],
                        "expected_decision": EXPECTED_DECISIONS.get(target["customer_id"], ""),
                        "decision_matches_expected": False,
                        "amount": float(target["amount"]),
                        "http_status": "",
                        "request_ok": False,
                        "client_elapsed_ms": round(elapsed_ms, 2),
                        "server_elapsed_s": "",
                        "decision": "",
                        "risk_score": "",
                        "risk_percent": "",
                        "risk_level": "",
                        "gray_zone_used": False,
                        "gray_zone_decision": "",
                        "gray_zone_elapsed_s": "",
                        "gray_zone_reasoning": "",
                        "llm_comparison_enabled": bool(args.run_llm_comparison),
                        "llm_comparison_elapsed_s": "",
                        "llm_comparison_indicator_count": 0,
                        "llm_comparison_score": "",
                        "llm_comparison_decision": "",
                        "rate_limited_http_429": False,
                        "rate_limited_signal": False,
                        "rate_limited_reason": "",
                        "error": str(exc),
                        "response_excerpt": "",
                    }
                    gemini_row = {
                        "request_id": seq_id,
                        "iteration": iteration,
                        "started_at": utc_iso(started),
                        "customer_id": target["customer_id"],
                        "withdrawal_id": target["withdrawal_id"],
                        "model": GEMINI_MODEL,
                        "http_status": "",
                        "request_ok": False,
                        "client_elapsed_ms": round(elapsed_ms, 2),
                        "server_elapsed_s": "",
                        "decision": "",
                        "gray_zone_used": False,
                        "gray_zone_decision": "",
                        "gray_zone_elapsed_s": "",
                        "gray_zone_reasoning": "",
                        "llm_comparison_enabled": bool(args.run_llm_comparison),
                        "llm_comparison_elapsed_s": "",
                        "llm_comparison_indicator_count": 0,
                        "llm_avg_indicator_elapsed_s": "",
                        "llm_comparison_score": "",
                        "llm_comparison_decision": "",
                        "rate_limited_http_429": False,
                        "rate_limited_signal": False,
                        "rate_limited_reason": "",
                        "error": str(exc),
                    }
                    return {
                        "request_row": request_row,
                        "gemini_row": gemini_row,
                        "indicator_rows": [],
                    }

        tasks = []
        for seq_id, (iteration, target) in enumerate(workload, start=1):
            tasks.append(asyncio.create_task(one_request(seq_id, iteration, target)))

        raw_results = await asyncio.gather(*tasks)

    results = [r["request_row"] for r in raw_results]
    gemini_rows = [r["gemini_row"] for r in raw_results]
    gemini_indicator_rows: list[dict[str, Any]] = []
    for r in raw_results:
        gemini_indicator_rows.extend(r["indicator_rows"])

    scenario_rows = []
    for target in targets:
        cid = target["customer_id"]
        scenario_rows.append(
            {
                "customer_id": cid,
                "withdrawal_id": target["withdrawal_id"],
                "amount": float(target["amount"]),
                "expected_decision": EXPECTED_DECISIONS.get(cid, ""),
                "recipient_name": target["recipient_name"],
                "customer_country": target["customer_country"],
                "requested_at": utc_iso(target["requested_at"]),
            }
        )

    return results, scenario_rows, gemini_rows, gemini_indicator_rows, url


def scan_docker_rate_limit_logs(container: str, since: datetime) -> tuple[list[dict[str, Any]], str]:
    since_iso = utc_iso(since)
    cmd = ["docker", "logs", "--since", since_iso, "--timestamps", container]
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except Exception as exc:
        return [], str(exc)

    joined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if proc.returncode != 0:
        return [], joined.strip()[:600]

    events: list[dict[str, Any]] = []
    for line in joined.splitlines():
        if "Gemini rate limit: waiting" not in line:
            continue
        wait_match = re.search(r"waiting\s+([0-9]+(?:\.[0-9]+)?)s", line)
        wait_s = float(wait_match.group(1)) if wait_match else 0.0
        ts = line.split(" ", 1)[0] if " " in line else ""
        events.append({"timestamp": ts, "wait_s": wait_s, "line": line[:1000]})
    return events, ""


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_summary(
    rows: list[dict[str, Any]],
    args: argparse.Namespace,
    url: str,
    started_at: datetime,
    finished_at: datetime,
    docker_events: list[dict[str, Any]],
    docker_log_error: str,
    missing_customers: list[str],
) -> dict[str, Any]:
    ok_rows = [r for r in rows if r["request_ok"]]
    client_latencies = [float(r["client_elapsed_ms"]) for r in rows]
    server_latencies = [float(r["server_elapsed_s"]) for r in ok_rows if r["server_elapsed_s"] != ""]

    decision_counts = Counter(r["decision"] for r in ok_rows if r["decision"])
    status_counts = Counter(str(r["http_status"]) for r in rows if r["http_status"] != "")
    rate_limited_signal_count = sum(1 for r in rows if r["rate_limited_signal"])
    rate_limited_http_429_count = sum(1 for r in rows if r["rate_limited_http_429"])

    docker_wait_total = round(sum(float(e["wait_s"]) for e in docker_events), 3)

    return {
        "run_started_at": utc_iso(started_at),
        "run_finished_at": utc_iso(finished_at),
        "run_duration_s": round((finished_at - started_at).total_seconds(), 3),
        "base_url": args.base_url,
        "endpoint_url": url,
        "db_dsn": args.db_dsn,
        "iterations": args.iterations,
        "concurrency": args.concurrency,
        "timeout_s": args.timeout_s,
        "run_llm_comparison": bool(args.run_llm_comparison),
        "requested_customers": args.customer_ids,
        "missing_customers": ",".join(missing_customers),
        "total_requests": len(rows),
        "ok_requests": len(ok_rows),
        "error_requests": len(rows) - len(ok_rows),
        "client_ms_avg": round(sum(client_latencies) / len(client_latencies), 3) if client_latencies else 0.0,
        "client_ms_p50": round(percentile(client_latencies, 50), 3),
        "client_ms_p90": round(percentile(client_latencies, 90), 3),
        "client_ms_p95": round(percentile(client_latencies, 95), 3),
        "client_ms_p99": round(percentile(client_latencies, 99), 3),
        "server_elapsed_s_avg": round(sum(server_latencies) / len(server_latencies), 3) if server_latencies else 0.0,
        "rate_limited_signal_count": rate_limited_signal_count,
        "rate_limited_http_429_count": rate_limited_http_429_count,
        "docker_gemini_wait_event_count": len(docker_events),
        "docker_gemini_wait_total_s": docker_wait_total,
        "docker_log_error": docker_log_error,
        "decision_counts": dict(decision_counts),
        "status_counts": dict(status_counts),
    }


def print_human_summary(summary: dict[str, Any], output_dir: Path) -> None:
    print("=" * 70)
    print("Evaluate benchmark complete")
    print("=" * 70)
    print(f"Output dir: {output_dir}")
    print(f"Requests: {summary['total_requests']} total | {summary['ok_requests']} ok | {summary['error_requests']} errors")
    print(
        "Client latency (ms): "
        f"avg={summary['client_ms_avg']} p50={summary['client_ms_p50']} "
        f"p90={summary['client_ms_p90']} p95={summary['client_ms_p95']} p99={summary['client_ms_p99']}"
    )
    print(
        "Rate limit signals: "
        f"payload/http={summary['rate_limited_signal_count']} "
        f"http_429={summary['rate_limited_http_429_count']} "
        f"docker_wait_events={summary['docker_gemini_wait_event_count']}"
    )
    print(f"Decisions: {summary['decision_counts']}")


def main() -> None:
    args = parse_args()
    if not args.run_llm_comparison:
        raise ValueError("This benchmark targets LLM route only. Use --run-llm-comparison.")

    if not args.skip_healthcheck:
        asyncio.run(
            wait_for_api_ready(
                base_url=args.base_url,
                path=args.healthcheck_path,
                timeout_s=args.healthcheck_timeout_s,
            )
        )

    selected_customers = [c.strip() for c in args.customer_ids.split(",") if c.strip()]
    run_started_at = utc_now()

    targets, missing_customers = get_targets(
        db_dsn=args.db_dsn,
        customer_ids=selected_customers,
        fallback_sample_size=args.fallback_sample_size,
    )
    if not targets:
        raise RuntimeError("No withdrawal records found for benchmark requests.")

    rows, _scenario_rows, gemini_rows, gemini_indicator_rows, url = asyncio.run(
        run_requests(args, targets, run_started_at)
    )

    docker_events: list[dict[str, Any]] = []
    docker_log_error = ""
    if not args.skip_docker_log_scan:
        docker_events, docker_log_error = scan_docker_rate_limit_logs(
            container=args.docker_log_container,
            since=run_started_at,
        )

    run_finished_at = utc_now()
    run_id = run_started_at.strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = build_summary(
        rows=rows,
        args=args,
        url=url,
        started_at=run_started_at,
        finished_at=run_finished_at,
        docker_events=docker_events,
        docker_log_error=docker_log_error,
        missing_customers=missing_customers,
    )

    concise_rows = build_llm_concise_rows(
        run_id=run_id,
        request_rows=gemini_rows,
        indicator_rows=gemini_indicator_rows,
        summary=summary,
    )
    write_csv(output_dir / "llm_benchmark_concise.csv", concise_rows)

    print_human_summary(summary, output_dir)


if __name__ == "__main__":
    main()

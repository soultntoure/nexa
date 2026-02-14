"""Benchmark adaptive blend weighting (rule_engine vs investigators).

This script drives live API calls and measures how customer-specific blend weights
move when officer decisions favor either rule-engine outcomes or investigator
outcomes.

Outputs are written to:
    outputs/blend_feedback_benchmark/<customer>_<timestamp>/
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from http.client import RemoteDisconnected
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import psycopg2

from app.agentic_system.prompts.investigators import build_investigator_prompt
from app.agentic_system.prompts.triage import TRIAGE_VERDICT_PROMPT
from app.core.weight_context import (
    BOOSTED_THRESHOLD,
    DAMPENED_THRESHOLD,
    INVESTIGATOR_INDICATORS,
    build_weight_context,
)


DEFAULT_BASE_URL = "http://localhost:18080"
DEFAULT_OUTPUT_ROOT = Path("outputs") / "blend_feedback_benchmark"
DEFAULT_OFFICER_ID = "officer-benchmark-001"
DEFAULT_DB_DSN = "postgresql+asyncpg://user:changeme@localhost:15432/fraud_detection"
DEFAULT_SWEEP_CUSTOMERS = ["CUST-011", "CUST-013", "CUST-014"]
DEFAULT_BOUNDARY_PHASE = "favor_rule"
DEFAULT_MAX_BOUNDARY_CYCLES = 8

MAX_RECIPIENT_ACCOUNT_LEN = 64
MAX_DEVICE_FP_LEN = 64
AUTO_SUFFIX_RE = re.compile(r"(?:-B\d{3}|-probe\d*|-probe)+$", re.IGNORECASE)

BLOCK_ACTIONS = {"blocked", "block"}


@dataclass
class CustomerTemplate:
    customer_id: str
    amount: float
    recipient_name: str
    recipient_account: str
    ip_address: str
    device_fingerprint: str
    customer_country: str


def _sync_dsn() -> str:
    return os.getenv("POSTGRES_URL", DEFAULT_DB_DSN).replace("+asyncpg", "")


def _http_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 90.0,
) -> tuple[int, dict[str, Any], float]:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = Request(url=url, data=data, headers=headers, method=method)
    t0 = time.perf_counter()
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            body = _parse_json_body(raw)
            return resp.status, body, time.perf_counter() - t0
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        body = _parse_json_body(raw)
        if not body:
            body = {"detail": raw.strip() or str(exc)}
        return exc.code, body, time.perf_counter() - t0
    except (URLError, RemoteDisconnected, TimeoutError, OSError) as exc:
        return 599, {"detail": str(exc)}, time.perf_counter() - t0


def _parse_json_body(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"detail": raw.strip()}
    return parsed if isinstance(parsed, dict) else {"data": parsed}


def _clean_template_value(value: str | None, max_len: int) -> str:
    text = (value or "").strip()
    if not text:
        return ""

    while True:
        cleaned = AUTO_SUFFIX_RE.sub("", text)
        if cleaned == text:
            break
        text = cleaned

    if not text:
        text = (value or "").strip()

    return text[:max_len]


def _append_cycle_suffix(base: str, cycle_index: int, max_len: int) -> str:
    suffix = f"-B{cycle_index:03d}"
    base_clean = _clean_template_value(base, max_len=max_len)
    allowed = max_len - len(suffix)
    if allowed <= 0:
        return suffix[-max_len:]
    return f"{base_clean[:allowed]}{suffix}"


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def fetch_customer_template(customer_id: str) -> CustomerTemplate:
    query = """
    SELECT
        c.external_id,
        c.country,
        w.amount,
        w.recipient_name,
        w.recipient_account,
        w.ip_address,
        w.device_fingerprint
    FROM customers c
    JOIN withdrawals w ON w.customer_id = c.id
    WHERE c.external_id = %s
    ORDER BY w.created_at DESC
    LIMIT 1
    """

    with psycopg2.connect(_sync_dsn()) as conn, conn.cursor() as cur:
        cur.execute(query, (customer_id,))
        row = cur.fetchone()

    if row is None:
        raise ValueError(f"Customer template not found for {customer_id}")

    country = (row[1] or "GBR").upper()
    if len(country) < 3:
        country = (country + "XXX")[:3]

    recipient_account = _clean_template_value(
        row[4] or "ACC-BENCH-001",
        max_len=MAX_RECIPIENT_ACCOUNT_LEN,
    )
    if not recipient_account:
        recipient_account = "ACC-BENCH-001"

    device_fingerprint = _clean_template_value(
        row[6] or "dfp-benchmark-seed",
        max_len=MAX_DEVICE_FP_LEN,
    )
    if not device_fingerprint:
        device_fingerprint = "dfp-benchmark-seed"

    return CustomerTemplate(
        customer_id=row[0],
        amount=float(row[2] or 1000.0),
        recipient_name=row[3] or "Benchmark Recipient",
        recipient_account=recipient_account,
        ip_address=row[5] or "185.199.110.153",
        device_fingerprint=device_fingerprint,
        customer_country=country,
    )


def fetch_rule_decision(evaluation_id: str) -> tuple[str, str]:
    query = """
    SELECT decision, investigation_data
    FROM evaluations
    WHERE id = %s::uuid
    """

    with psycopg2.connect(_sync_dsn()) as conn, conn.cursor() as cur:
        cur.execute(query, (evaluation_id,))
        row = cur.fetchone()

    if row is None:
        return "", ""

    final_decision = str(row[0] or "").strip().lower()
    investigation_data = _as_dict(row[1])
    rule_engine = investigation_data.get("rule_engine")
    if isinstance(rule_engine, dict):
        rule_decision = str(rule_engine.get("decision") or "").strip().lower()
    else:
        rule_decision = ""

    return rule_decision or final_decision, final_decision


def fetch_active_profile_context(
    customer_id: str,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    query = """
    SELECT p.indicator_weights, p.blend_weights, p.recalculated_at, p.created_at
    FROM customer_weight_profiles p
    JOIN customers c ON c.id = p.customer_id
    WHERE c.external_id = %s AND p.is_active = true
    ORDER BY p.created_at DESC
    LIMIT 1
    """

    with psycopg2.connect(_sync_dsn()) as conn, conn.cursor() as cur:
        cur.execute(query, (customer_id,))
        row = cur.fetchone()

    if row is None:
        return {}, {}, ""

    indicator_weights = _as_dict(row[0])
    blend_weights = _as_dict(row[1])
    updated_at = row[2] or row[3]
    updated_at_str = updated_at.isoformat() if updated_at else ""
    return indicator_weights, blend_weights, updated_at_str


def _prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def render_prompt_rows(
    *,
    customer_id: str,
    phase: str,
    cycle: int,
    calibration_step: int,
    sample_count: int,
    profile_updated_at: str,
    indicator_weights: dict[str, Any],
    blend_weights: dict[str, Any],
    previous_hashes: dict[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    global_context = build_weight_context(indicator_weights, blend_weights)
    triage_prompt = TRIAGE_VERDICT_PROMPT.format(weight_context=global_context)
    rows.append(
        _prompt_row(
            customer_id=customer_id,
            phase=phase,
            cycle=cycle,
            calibration_step=calibration_step,
            sample_count=sample_count,
            profile_updated_at=profile_updated_at,
            prompt_kind="triage",
            investigator="",
            prompt_scope="global",
            context_text=global_context,
            full_prompt=triage_prompt,
            previous_hashes=previous_hashes,
        )
    )

    for investigator_name, relevant in INVESTIGATOR_INDICATORS.items():
        filtered_context = build_weight_context(
            indicator_weights,
            blend_weights,
            relevant_indicators=relevant,
        )
        full_prompt = build_investigator_prompt(
            investigator_name,
            weight_context=filtered_context,
        )
        rows.append(
            _prompt_row(
                customer_id=customer_id,
                phase=phase,
                cycle=cycle,
                calibration_step=calibration_step,
                sample_count=sample_count,
                profile_updated_at=profile_updated_at,
                prompt_kind="investigator",
                investigator=investigator_name,
                prompt_scope="filtered",
                context_text=filtered_context,
                full_prompt=full_prompt,
                previous_hashes=previous_hashes,
            )
        )

    return rows


def _prompt_row(
    *,
    customer_id: str,
    phase: str,
    cycle: int,
    calibration_step: int,
    sample_count: int,
    profile_updated_at: str,
    prompt_kind: str,
    investigator: str,
    prompt_scope: str,
    context_text: str,
    full_prompt: str,
    previous_hashes: dict[str, str],
) -> dict[str, Any]:
    key = f"{prompt_kind}:{investigator or 'none'}"
    prompt_hash = _prompt_hash(full_prompt)
    previous_hash = previous_hashes.get(key, "")
    changed = prompt_hash != previous_hash
    previous_hashes[key] = prompt_hash

    return {
        "customer_id": customer_id,
        "phase": phase,
        "cycle": cycle,
        "calibration_step": calibration_step,
        "sample_count": sample_count,
        "profile_updated_at": profile_updated_at,
        "prompt_kind": prompt_kind,
        "investigator": investigator,
        "prompt_scope": prompt_scope,
        "context_text": context_text,
        "full_prompt": full_prompt,
        "prompt_hash": prompt_hash,
        "previous_prompt_hash": previous_hash,
        "changed_from_previous": changed,
        "prompt_char_count": len(full_prompt),
        "context_char_count": len(context_text),
    }


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def find_boundary_crossings(indicator_weights: dict[str, Any]) -> list[dict[str, Any]]:
    crossings: list[dict[str, Any]] = []

    for name, raw in indicator_weights.items():
        if not isinstance(raw, dict):
            continue

        multiplier = _to_float(raw.get("multiplier"), default=1.0)
        sample_size = _to_int(
            raw.get("sample_size")
            or raw.get("total_fires")
            or raw.get("total")
            or 0,
            default=0,
        )
        precision = _to_float(raw.get("precision"), default=0.0)

        if sample_size < 3:
            continue

        direction = ""
        if multiplier < DAMPENED_THRESHOLD:
            direction = "dampened"
        elif multiplier > BOOSTED_THRESHOLD:
            direction = "boosted"
        if not direction:
            continue

        crossings.append(
            {
                "indicator": name,
                "direction": direction,
                "multiplier": round(multiplier, 4),
                "sample_size": sample_size,
                "precision": round(precision, 4),
            }
        )

    return sorted(
        crossings,
        key=lambda x: (x["direction"], x["multiplier"], x["indicator"]),
    )


def get_weights_snapshot(base_url: str, customer_id: str) -> dict[str, Any]:
    status, body, _ = _http_json(
        "GET",
        f"{base_url}/api/customers/{customer_id}/weights",
        payload=None,
        timeout=30,
    )
    if status != 200:
        raise RuntimeError(f"weights endpoint failed ({status}): {body}")
    return body


def wait_for_profile_refresh(
    base_url: str,
    customer_id: str,
    previous_last_updated: str | None,
    previous_sample_count: int,
    timeout_s: int,
) -> tuple[dict[str, Any], float]:
    started = time.perf_counter()
    while time.perf_counter() - started < timeout_s:
        snap = get_weights_snapshot(base_url, customer_id)
        if (
            snap.get("last_updated") != previous_last_updated
            or int(snap.get("sample_count") or 0) != previous_sample_count
        ):
            return snap, time.perf_counter() - started
        time.sleep(1)

    return get_weights_snapshot(base_url, customer_id), time.perf_counter() - started


def weighted_investigator_average(findings: list[dict[str, Any]]) -> float | None:
    total_weight = 0.0
    weighted_sum = 0.0

    for finding in findings:
        score = finding.get("score")
        confidence = finding.get("confidence")
        if score is None or confidence is None:
            continue
        try:
            score_f = float(str(score))
            conf_f = float(str(confidence))
        except (TypeError, ValueError):
            continue
        if not (0.0 <= score_f <= 1.0 and 0.0 <= conf_f <= 1.0):
            continue

        weight = max(conf_f, 0.05)
        total_weight += weight
        weighted_sum += score_f * weight

    if total_weight == 0:
        return None
    return weighted_sum / total_weight


def choose_officer_action(phase: str, rule_decision: str, inv_avg: float) -> str:
    if phase == "favor_rule":
        return "blocked" if rule_decision in BLOCK_ACTIONS else "approved"
    if phase == "favor_investigators":
        return "blocked" if inv_avg >= 0.5 else "approved"
    raise ValueError(f"Unknown phase: {phase}")


def run_cycle(
    *,
    base_url: str,
    template: CustomerTemplate,
    customer_id: str,
    officer_id: str,
    phase: str,
    cycle_index: int,
    poll_timeout: int,
) -> dict[str, Any]:
    before = get_weights_snapshot(base_url, customer_id)
    before_blend = before.get("blend", {}).get("customer", {})
    before_rule_w = float(before_blend.get("rule_engine", 0.6))
    before_inv_w = float(before_blend.get("investigators", 0.4))
    before_last_updated = before.get("last_updated")
    before_samples = int(before.get("sample_count") or 0)

    wid = str(uuid.uuid4())
    payload = {
        "withdrawal_id": wid,
        "customer_id": template.customer_id,
        "amount": round(template.amount * (1 + (0.01 * (cycle_index % 3))), 2),
        "recipient_name": template.recipient_name,
        "recipient_account": _append_cycle_suffix(
            template.recipient_account,
            cycle_index,
            MAX_RECIPIENT_ACCOUNT_LEN,
        ),
        "ip_address": template.ip_address,
        "device_fingerprint": _append_cycle_suffix(
            template.device_fingerprint,
            cycle_index,
            MAX_DEVICE_FP_LEN,
        ),
        "customer_country": template.customer_country,
    }

    inv_status, inv_body, inv_elapsed = _http_json(
        "POST",
        f"{base_url}/api/withdrawals/investigate",
        payload=payload,
        timeout=120,
    )
    if inv_status != 200:
        return {
            "phase": phase,
            "cycle": cycle_index,
            "status": "investigate_error",
            "http_status": inv_status,
            "error": json.dumps(inv_body),
            "investigate_elapsed_s": round(inv_elapsed, 3),
        }

    evaluation_id = str(inv_body.get("evaluation_id") or "")
    findings = inv_body.get("investigators") or []
    inv_avg = weighted_investigator_average(findings)
    if not evaluation_id:
        return {
            "phase": phase,
            "cycle": cycle_index,
            "status": "missing_evaluation_id",
            "investigate_elapsed_s": round(inv_elapsed, 3),
        }
    if not findings or inv_avg is None:
        return {
            "phase": phase,
            "cycle": cycle_index,
            "status": "skipped_no_investigators",
            "evaluation_id": evaluation_id,
            "investigate_elapsed_s": round(inv_elapsed, 3),
            "rule_decision_api": inv_body.get("decision"),
        }

    rule_decision, final_decision = fetch_rule_decision(evaluation_id)
    action = choose_officer_action(phase, rule_decision, inv_avg)

    decision_payload = {
        "withdrawal_id": wid,
        "evaluation_id": evaluation_id,
        "officer_id": officer_id,
        "action": action,
        "reason": f"blend benchmark {phase} cycle {cycle_index}",
    }
    dec_status, dec_body, dec_elapsed = _http_json(
        "POST",
        f"{base_url}/api/payout/decision",
        payload=decision_payload,
        timeout=60,
    )
    if dec_status != 200:
        return {
            "phase": phase,
            "cycle": cycle_index,
            "status": "decision_error",
            "http_status": dec_status,
            "error": json.dumps(dec_body),
            "evaluation_id": evaluation_id,
            "rule_decision": rule_decision,
            "final_decision": final_decision,
            "investigator_avg": round(inv_avg, 4),
            "investigator_count": len(findings),
            "investigate_elapsed_s": round(inv_elapsed, 3),
            "decision_elapsed_s": round(dec_elapsed, 3),
        }

    after, wait_s = wait_for_profile_refresh(
        base_url,
        customer_id,
        before_last_updated,
        before_samples,
        timeout_s=poll_timeout,
    )
    after_blend = after.get("blend", {}).get("customer", {})
    after_rule_w = float(after_blend.get("rule_engine", before_rule_w))
    after_inv_w = float(after_blend.get("investigators", before_inv_w))

    return {
        "phase": phase,
        "cycle": cycle_index,
        "status": "success",
        "customer_id": customer_id,
        "evaluation_id": evaluation_id,
        "rule_decision": rule_decision,
        "final_decision": final_decision,
        "officer_action": action,
        "investigator_avg": round(inv_avg, 4),
        "investigator_count": len(findings),
        "before_rule_weight": round(before_rule_w, 4),
        "after_rule_weight": round(after_rule_w, 4),
        "delta_rule_weight": round(after_rule_w - before_rule_w, 4),
        "before_investigator_weight": round(before_inv_w, 4),
        "after_investigator_weight": round(after_inv_w, 4),
        "delta_investigator_weight": round(after_inv_w - before_inv_w, 4),
        "before_sample_count": before_samples,
        "after_sample_count": int(after.get("sample_count") or before_samples),
        "investigate_elapsed_s": round(inv_elapsed, 3),
        "decision_elapsed_s": round(dec_elapsed, 3),
        "feedback_wait_s": round(wait_s, 3),
    }


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def phase_summary(rows: list[dict[str, Any]], phase: str) -> dict[str, Any]:
    success = [r for r in rows if r.get("phase") == phase and r.get("status") == "success"]
    return {
        "phase": phase,
        "attempts": len([r for r in rows if r.get("phase") == phase]),
        "successes": len(success),
        "avg_rule_weight_delta": round(mean([float(r["delta_rule_weight"]) for r in success]), 4),
        "avg_investigator_weight_delta": round(mean([float(r["delta_investigator_weight"]) for r in success]), 4),
        "avg_investigator_score": round(mean([float(r["investigator_avg"]) for r in success]), 4),
        "avg_feedback_wait_s": round(mean([float(r["feedback_wait_s"]) for r in success]), 3),
    }


def write_outputs(
    out_dir: Path,
    rows: list[dict[str, Any]],
    prompt_rows: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / "blend_feedback_cycles.csv"
    fieldnames = sorted({k for row in rows for k in row.keys()})
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary_json = out_dir / "blend_feedback_summary.json"
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    prompt_csv = out_dir / "prompt_context_evolution.csv"
    prompt_fields = sorted({k for row in prompt_rows for k in row.keys()}) if prompt_rows else []
    with prompt_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=prompt_fields)
        if prompt_fields:
            writer.writeheader()
            writer.writerows(prompt_rows)

    summary_txt = out_dir / "blend_feedback_summary.txt"
    lines = [
        "Blend Feedback Benchmark",
        "=" * 26,
        f"Customer: {summary['customer_id']}",
        f"Base URL: {summary['base_url']}",
        f"Run At: {summary['run_at']}",
        "",
        f"Initial Blend: {summary['initial_blend']}",
        f"Final Blend:   {summary['final_blend']}",
        f"Prompt Snapshots: {summary.get('prompt_snapshots', 0)}",
        "",
        "Phase Summaries:",
    ]
    for p in summary["phase_summaries"]:
        lines.append(
            f"- {p['phase']}: successes={p['successes']}/{p['attempts']}, "
            f"avg_rule_delta={p['avg_rule_weight_delta']}, "
            f"avg_inv_delta={p['avg_investigator_weight_delta']}"
        )
    summary_txt.write_text("\n".join(lines), encoding="utf-8")


def write_sweep_outputs(
    sweep_dir: Path,
    all_rows: list[dict[str, Any]],
    all_prompt_rows: list[dict[str, Any]],
    sweep_summary: dict[str, Any],
) -> None:
    sweep_dir.mkdir(parents=True, exist_ok=True)

    csv_path = sweep_dir / "blend_feedback_sweep_cycles.csv"
    fieldnames = sorted({k for row in all_rows for k in row.keys()}) if all_rows else []
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(all_rows)

    summary_json = sweep_dir / "blend_feedback_sweep_summary.json"
    summary_json.write_text(json.dumps(sweep_summary, indent=2), encoding="utf-8")

    prompt_csv = sweep_dir / "prompt_context_evolution_sweep.csv"
    prompt_fields = (
        sorted({k for row in all_prompt_rows for k in row.keys()}) if all_prompt_rows else []
    )
    with prompt_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=prompt_fields)
        if prompt_fields:
            writer.writeheader()
            writer.writerows(all_prompt_rows)

    summary_txt = sweep_dir / "blend_feedback_sweep_summary.txt"
    lines = [
        "Blend Feedback Sweep Benchmark",
        "=" * 31,
        f"Base URL: {sweep_summary['base_url']}",
        f"Run At: {sweep_summary['run_at']}",
        f"Customers: {', '.join(sweep_summary['customers'])}",
        f"Prompt Snapshots: {sweep_summary.get('prompt_snapshots', 0)}",
        "",
        "Overall Phase Summaries:",
    ]
    for p in sweep_summary["overall_phase_summaries"]:
        lines.append(
            f"- {p['phase']}: successes={p['successes']}/{p['attempts']}, "
            f"avg_rule_delta={p['avg_rule_weight_delta']}, "
            f"avg_inv_delta={p['avg_investigator_weight_delta']}"
        )
    summary_txt.write_text("\n".join(lines), encoding="utf-8")


def parse_customer_ids(raw: str) -> list[str]:
    if not raw:
        return []

    values = [item.strip().upper() for item in raw.split(",") if item.strip()]
    seen: set[str] = set()
    result: list[str] = []
    for cid in values:
        if cid in seen:
            continue
        seen.add(cid)
        result.append(cid)
    return result


def run_customer_benchmark(
    *,
    customer_id: str,
    base_url: str,
    rule_cycles: int,
    investigator_cycles: int,
    max_attempt_multiplier: int,
    poll_timeout: int,
    officer_id: str,
    reset_first: bool,
    out_dir: Path,
    require_boundary_cross: bool,
    boundary_phase: str,
    max_boundary_cycles: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    template = fetch_customer_template(customer_id)

    if reset_first:
        reset_payload = {
            "reason": "blend feedback benchmark reset",
            "updated_by": officer_id,
        }
        status, body, _ = _http_json(
            "POST",
            f"{base_url}/api/customers/{customer_id}/weights/reset",
            payload=reset_payload,
            timeout=30,
        )
        if status != 200:
            raise RuntimeError(f"Failed reset before benchmark ({status}): {body}")

    initial = get_weights_snapshot(base_url, customer_id)
    rows: list[dict[str, Any]] = []
    prompt_rows: list[dict[str, Any]] = []
    prompt_hashes: dict[str, str] = {}
    calibration_step = 0
    boundary_crossed = False
    boundary_cross_step = 0
    boundary_cross_phase = ""
    boundary_crossings: list[dict[str, Any]] = []

    initial_indicator_weights, initial_blend_weights, initial_profile_updated_at = (
        fetch_active_profile_context(customer_id)
    )
    prompt_rows.extend(
        render_prompt_rows(
            customer_id=customer_id,
            phase="baseline",
            cycle=0,
            calibration_step=calibration_step,
            sample_count=int(initial.get("sample_count") or 0),
            profile_updated_at=initial_profile_updated_at,
            indicator_weights=initial_indicator_weights,
            blend_weights=initial_blend_weights,
            previous_hashes=prompt_hashes,
        )
    )

    initial_crossings = find_boundary_crossings(initial_indicator_weights)
    if initial_crossings:
        boundary_crossed = True
        boundary_cross_step = 0
        boundary_cross_phase = "baseline"
        boundary_crossings = initial_crossings

    phase_plan = [
        ("favor_rule", rule_cycles),
        ("favor_investigators", investigator_cycles),
    ]

    for phase, target_successes in phase_plan:
        successes = 0
        attempts = 0
        max_attempts = max(
            target_successes * max(max_attempt_multiplier, 1),
            target_successes,
        )

        print(f"\n[{customer_id}] phase={phase} target_successes={target_successes} max_attempts={max_attempts}")
        while successes < target_successes and attempts < max_attempts:
            attempts += 1
            cycle_record = run_cycle(
                base_url=base_url,
                template=template,
                customer_id=customer_id,
                officer_id=officer_id,
                phase=phase,
                cycle_index=attempts,
                poll_timeout=poll_timeout,
            )
            cycle_record.setdefault("customer_id", customer_id)
            rows.append(cycle_record)

            status = cycle_record.get("status")
            print(
                f"  attempt={attempts} status={status} "
                f"rule_dec={cycle_record.get('rule_decision')} "
                f"officer={cycle_record.get('officer_action')} "
                f"delta_rule={cycle_record.get('delta_rule_weight')}"
            )

            if status == "success":
                successes += 1
                calibration_step += 1
                indicator_weights, blend_weights, profile_updated_at = (
                    fetch_active_profile_context(customer_id)
                )
                if not boundary_crossed:
                    crossings = find_boundary_crossings(indicator_weights)
                    if crossings:
                        boundary_crossed = True
                        boundary_cross_step = calibration_step
                        boundary_cross_phase = phase
                        boundary_crossings = crossings
                        print(
                            f"  boundary crossed at step={calibration_step} phase={phase} "
                            f"count={len(crossings)}"
                        )
                prompt_rows.extend(
                    render_prompt_rows(
                        customer_id=customer_id,
                        phase=phase,
                        cycle=attempts,
                        calibration_step=calibration_step,
                        sample_count=int(cycle_record.get("after_sample_count") or 0),
                        profile_updated_at=profile_updated_at,
                        indicator_weights=indicator_weights,
                        blend_weights=blend_weights,
                        previous_hashes=prompt_hashes,
                    )
                )

    extra_boundary_cycles = 0
    if require_boundary_cross and not boundary_crossed:
        print(
            f"\n[{customer_id}] forcing boundary-cross phase={boundary_phase} "
            f"max_extra={max_boundary_cycles}"
        )
        while extra_boundary_cycles < max_boundary_cycles and not boundary_crossed:
            extra_boundary_cycles += 1
            cycle_index = len(rows) + 1
            cycle_record = run_cycle(
                base_url=base_url,
                template=template,
                customer_id=customer_id,
                officer_id=officer_id,
                phase=boundary_phase,
                cycle_index=cycle_index,
                poll_timeout=poll_timeout,
            )
            cycle_record.setdefault("customer_id", customer_id)
            cycle_record["forced_boundary_cycle"] = True
            rows.append(cycle_record)

            status = cycle_record.get("status")
            print(
                f"  forced attempt={extra_boundary_cycles} status={status} "
                f"delta_rule={cycle_record.get('delta_rule_weight')}"
            )

            if status != "success":
                continue

            calibration_step += 1
            indicator_weights, blend_weights, profile_updated_at = fetch_active_profile_context(customer_id)
            crossings = find_boundary_crossings(indicator_weights)
            if crossings:
                boundary_crossed = True
                boundary_cross_step = calibration_step
                boundary_cross_phase = boundary_phase
                boundary_crossings = crossings
                print(
                    f"  boundary crossed at step={calibration_step} phase={boundary_phase} "
                    f"count={len(crossings)}"
                )

            prompt_rows.extend(
                render_prompt_rows(
                    customer_id=customer_id,
                    phase=boundary_phase,
                    cycle=cycle_index,
                    calibration_step=calibration_step,
                    sample_count=int(cycle_record.get("after_sample_count") or 0),
                    profile_updated_at=profile_updated_at,
                    indicator_weights=indicator_weights,
                    blend_weights=blend_weights,
                    previous_hashes=prompt_hashes,
                )
            )

    final = get_weights_snapshot(base_url, customer_id)

    summary = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "customer_id": customer_id,
        "rule_cycles_target": rule_cycles,
        "investigator_cycles_target": investigator_cycles,
        "reset_first": reset_first,
        "initial_blend": initial.get("blend", {}).get("customer", {}),
        "final_blend": final.get("blend", {}).get("customer", {}),
        "initial_sample_count": int(initial.get("sample_count") or 0),
        "final_sample_count": int(final.get("sample_count") or 0),
        "phase_summaries": [
            phase_summary(rows, "favor_rule"),
            phase_summary(rows, "favor_investigators"),
        ],
        "boundary_cross_required": require_boundary_cross,
        "boundary_crossed": boundary_crossed,
        "boundary_cross_step": boundary_cross_step,
        "boundary_cross_phase": boundary_cross_phase,
        "boundary_crossings": boundary_crossings,
        "extra_boundary_cycles": extra_boundary_cycles,
        "prompt_snapshots": len(prompt_rows),
        "rows": len(rows),
    }

    write_outputs(out_dir, rows, prompt_rows, summary)
    return rows, summary, prompt_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark blend-weight adaptation via live API")
    parser.add_argument("--customer-id", default="CUST-012", help="Customer external id")
    parser.add_argument(
        "--customer-ids",
        default="",
        help="Comma-separated customer ids for sweep mode (ex: CUST-011,CUST-012)",
    )
    parser.add_argument(
        "--sweep",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run benchmark sweep across multiple customers",
    )
    parser.add_argument("--rule-cycles", type=int, default=2, help="Successful cycles that favor rule")
    parser.add_argument("--investigator-cycles", type=int, default=1, help="Successful cycles that favor investigators")
    parser.add_argument("--max-attempt-multiplier", type=int, default=4, help="Attempts cap multiplier per phase")
    parser.add_argument(
        "--require-boundary-cross",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Force extra cycles until multiplier crosses context boundary",
    )
    parser.add_argument(
        "--boundary-phase",
        default=DEFAULT_BOUNDARY_PHASE,
        choices=["favor_rule", "favor_investigators"],
        help="Phase to use when forcing boundary crossing",
    )
    parser.add_argument(
        "--max-boundary-cycles",
        type=int,
        default=DEFAULT_MAX_BOUNDARY_CYCLES,
        help="Maximum extra cycles for forced boundary crossing",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base url")
    parser.add_argument("--poll-timeout", type=int, default=45, help="Seconds to wait for async profile refresh")
    parser.add_argument("--officer-id", default=DEFAULT_OFFICER_ID, help="Officer id for decision endpoint")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Output root directory")
    parser.add_argument(
        "--reset-first",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Reset customer profile to baseline before running benchmark",
    )
    args = parser.parse_args()

    output_root = Path(args.output_root)
    requested_ids = parse_customer_ids(args.customer_ids)
    use_sweep = args.sweep or bool(requested_ids)

    if use_sweep:
        customer_ids = requested_ids or DEFAULT_SWEEP_CUSTOMERS
        sweep_dir = output_root / f"sweep_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        all_rows: list[dict[str, Any]] = []
        all_prompt_rows: list[dict[str, Any]] = []
        customer_summaries: list[dict[str, Any]] = []

        for customer_id in customer_ids:
            customer_dir = sweep_dir / customer_id.lower()
            rows, summary, prompt_rows = run_customer_benchmark(
                customer_id=customer_id,
                base_url=args.base_url,
                rule_cycles=args.rule_cycles,
                investigator_cycles=args.investigator_cycles,
                max_attempt_multiplier=args.max_attempt_multiplier,
                poll_timeout=args.poll_timeout,
                officer_id=args.officer_id,
                reset_first=args.reset_first,
                out_dir=customer_dir,
                require_boundary_cross=args.require_boundary_cross,
                boundary_phase=args.boundary_phase,
                max_boundary_cycles=args.max_boundary_cycles,
            )
            all_rows.extend(rows)
            all_prompt_rows.extend(prompt_rows)
            customer_summaries.append(summary)
            print(f"\n[{customer_id}] wrote artifacts to: {customer_dir}")

        sweep_summary = {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "base_url": args.base_url,
            "customers": customer_ids,
            "rule_cycles_target": args.rule_cycles,
            "investigator_cycles_target": args.investigator_cycles,
            "reset_first": args.reset_first,
            "rows": len(all_rows),
            "prompt_snapshots": len(all_prompt_rows),
            "overall_phase_summaries": [
                phase_summary(all_rows, "favor_rule"),
                phase_summary(all_rows, "favor_investigators"),
            ],
            "customer_summaries": customer_summaries,
        }
        write_sweep_outputs(sweep_dir, all_rows, all_prompt_rows, sweep_summary)

        print(f"\nWrote sweep artifacts to: {sweep_dir}")
        print(f"- {sweep_dir / 'blend_feedback_sweep_cycles.csv'}")
        print(f"- {sweep_dir / 'prompt_context_evolution_sweep.csv'}")
        print(f"- {sweep_dir / 'blend_feedback_sweep_summary.json'}")
        print(f"- {sweep_dir / 'blend_feedback_sweep_summary.txt'}")
        return

    out_dir = output_root / f"{args.customer_id.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    rows, summary, prompt_rows = run_customer_benchmark(
        customer_id=args.customer_id,
        base_url=args.base_url,
        rule_cycles=args.rule_cycles,
        investigator_cycles=args.investigator_cycles,
        max_attempt_multiplier=args.max_attempt_multiplier,
        poll_timeout=args.poll_timeout,
        officer_id=args.officer_id,
        reset_first=args.reset_first,
        out_dir=out_dir,
        require_boundary_cross=args.require_boundary_cross,
        boundary_phase=args.boundary_phase,
        max_boundary_cycles=args.max_boundary_cycles,
    )

    print(f"\nWrote benchmark artifacts to: {out_dir}")
    print(f"- {out_dir / 'blend_feedback_cycles.csv'}")
    print(f"- {out_dir / 'prompt_context_evolution.csv'}")
    print(f"- {out_dir / 'blend_feedback_summary.json'}")
    print(f"- {out_dir / 'blend_feedback_summary.txt'}")
    print(
        f"Rows captured: {len(rows)}, prompt snapshots: {len(prompt_rows)}, "
        f"final blend: {summary['final_blend']}"
    )


if __name__ == "__main__":
    main()

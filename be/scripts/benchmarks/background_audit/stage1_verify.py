"""Verify Stage 1 background audit outputs against quality gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Stage 1 audit outputs")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    base = Path(args.input_dir) / args.run_id
    results: dict[str, dict[str, object]] = {}
    all_pass = True

    # S1-G1: Output directory exists
    results["S1-G1"] = _check("Output dir exists", base.is_dir())

    # S1-G2: Required files exist
    required = [
        "run_summary.json", "clusters.json", "candidates.json",
        "embedding_metrics.json", "artifact_manifest.json", "audit_report.md",
    ]
    missing = [f for f in required if not (base / f).exists()]
    results["S1-G2"] = _check("Required files present", len(missing) == 0, missing)

    # S1-G3: Manifest checksums valid
    manifest_ok = _verify_manifest(base)
    results["S1-G3"] = _check("Manifest checksums valid", manifest_ok)

    # S1-G4: Schema version present
    manifest_path = base / "artifact_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        has_version = manifest.get("schema_version") is not None
    else:
        has_version = False
    results["S1-G4"] = _check("Schema version present", has_version)

    # S1-G5: Run summary valid
    summary_ok = _verify_run_summary(base / "run_summary.json")
    results["S1-G5"] = _check("Run summary valid", summary_ok)

    # S1-G6: Embedding model consistency
    emb_ok = _verify_embedding_model(base / "embedding_metrics.json")
    results["S1-G6"] = _check("Embedding model consistent", emb_ok)

    # S1-G7: Checkpoint completeness
    cp_dir = base / "checkpoints"
    cp_ok = cp_dir.is_dir() and any(cp_dir.iterdir()) if cp_dir.exists() else False
    results["S1-G7"] = _check("Checkpoints present", cp_ok)

    # S1-G8: Candidates have required fields
    cand_ok = _verify_candidates(base / "candidates.json")
    results["S1-G8"] = _check("Candidate schema valid", cand_ok)

    # S1-G9: Clusters file valid
    clusters_ok = _verify_json_array(base / "clusters.json")
    results["S1-G9"] = _check("Clusters file valid", clusters_ok)

    # S1-G10: No PII in audit report
    report_ok = _verify_no_pii(base / "audit_report.md")
    results["S1-G10"] = _check("No PII in report", report_ok)

    for gate, res in results.items():
        status = "PASS" if res["pass"] else "FAIL"
        all_pass = all_pass and bool(res["pass"])
        detail = f" ({res['detail']})" if res.get("detail") else ""
        print(f"  {gate}: {status}{detail}")

    receipt = {
        "run_id": args.run_id,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if all_pass else "fail",
        "gates": results,
    }
    receipt_path = base / "verify_result.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, default=str))

    end_receipt = base / "stage_end_receipt.json"
    end_receipt.write_text(json.dumps({
        "stage": "stage_1",
        "status": "pass" if all_pass else "fail",
        "run_id": args.run_id,
    }, indent=2))

    print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")
    sys.exit(0 if all_pass else 1)


def _check(
    name: str, passed: bool, detail: object = None,
) -> dict[str, object]:
    return {"name": name, "pass": passed, "detail": detail}


def _verify_manifest(base: Path) -> bool:
    path = base / "artifact_manifest.json"
    if not path.exists():
        return False
    manifest = json.loads(path.read_text())
    for rel, info in manifest.get("files", {}).items():
        fpath = base / rel
        if not fpath.exists():
            return False
        actual = hashlib.sha256(fpath.read_bytes()).hexdigest()
        if actual != info.get("sha256"):
            return False
    return True


def _verify_run_summary(path: Path) -> bool:
    if not path.exists():
        return False
    data = json.loads(path.read_text())
    return "run_id" in data and "total_units" in data


def _verify_embedding_model(path: Path) -> bool:
    if not path.exists():
        return False
    data = json.loads(path.read_text())
    return data.get("model") == "gemini-embedding-001"


def _verify_candidates(path: Path) -> bool:
    if not path.exists():
        return True  # 0 candidates is valid
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        return False
    for c in data:
        if "candidate_id" not in c or "quality_score" not in c:
            return False
    return True


def _verify_json_array(path: Path) -> bool:
    if not path.exists():
        return False
    data = json.loads(path.read_text())
    return isinstance(data, list)


def _verify_no_pii(path: Path) -> bool:
    if not path.exists():
        return True
    import re
    text = path.read_text()
    email = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    return email is None


if __name__ == "__main__":
    main()

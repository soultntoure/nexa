"""Trigger and poll a Stage 1 background audit run."""

from __future__ import annotations

import argparse
import sys
import time

import httpx

BASE = "http://localhost:18080/api/background-audits"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Stage 1 background audit")
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--run-mode", default="full")
    parser.add_argument("--timeout", type=int, default=300, help="Max wait seconds")
    args = parser.parse_args()

    with httpx.Client(timeout=30) as client:
        resp = client.post(f"{BASE}/trigger", json={
            "lookback_days": args.lookback_days,
            "run_mode": args.run_mode,
        })
        resp.raise_for_status()
        run_id = resp.json()["run_id"]
        print(f"Triggered run: {run_id}")

        deadline = time.time() + args.timeout
        while time.time() < deadline:
            status_resp = client.get(f"{BASE}/runs/{run_id}")
            status_resp.raise_for_status()
            data = status_resp.json()
            status = data["status"]
            print(f"  Status: {status} | Counters: {data.get('counters', {})}")

            if status == "completed":
                print(f"\nRun {run_id} completed successfully!")
                print(f"  Timings: {data.get('timings', {})}")
                print(f"  Counters: {data.get('counters', {})}")

                cand_resp = client.get(f"{BASE}/runs/{run_id}/candidates")
                cand_resp.raise_for_status()
                candidates = cand_resp.json().get("candidates", [])
                print(f"  Candidates: {len(candidates)}")
                for c in candidates:
                    print(f"    - {c['title']} (quality={c['quality_score']:.2f})")
                return

            if status == "failed":
                print(f"\nRun {run_id} FAILED: {data.get('error_message')}")
                sys.exit(1)

            time.sleep(5)

        print(f"\nTimeout waiting for run {run_id}")
        sys.exit(1)


if __name__ == "__main__":
    main()

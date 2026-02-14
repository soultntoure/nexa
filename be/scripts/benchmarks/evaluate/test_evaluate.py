"""Hit the /api/withdrawals/investigate endpoint for 3 test scenarios."""

import uuid
import httpx
import json
import sys

BASE = "http://localhost:18080"
TIMEOUT = 150.0


def _id(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"deriv.seed.{name}"))


SCENARIOS = [
    {
        "label": "Sarah Chen — Clean (expect APPROVE)",
        "body": {
            "withdrawal_id": _id("sarah.wd.pending"),
            "customer_id": "CUST-001",
            "amount": 500.00,
            "recipient_name": "Sarah Chen",
            "recipient_account": "GB29NWBK60161331926819",
            "ip_address": "51.148.20.30",
            "device_fingerprint": "f1e2d3c4b5a6f1e2d3c4b5a6f1e2d3c4",
            "customer_country": "GBR",
        },
    },
    {
        "label": "David Park — VPN Traveler (expect ESCALATE)",
        "body": {
            "withdrawal_id": _id("david.wd.pending"),
            "customer_id": "CUST-007",
            "amount": 1000.00,
            "recipient_name": "David Park",
            "recipient_account": "KR1234567890123456789012",
            "ip_address": "185.199.110.20",
            "device_fingerprint": "a1a2a3a4b5b6a1a2a3a4b5b6a1a2a3a4",
            "customer_country": "KOR",
        },
    },
    {
        "label": "Victor Petrov — Fraud (expect BLOCK)",
        "body": {
            "withdrawal_id": _id("victor.wd.pending"),
            "customer_id": "CUST-011",
            "amount": 2990.00,
            "recipient_name": "Victor Petrov",
            "recipient_account": "RU0123456789012345678901234",
            "ip_address": "95.173.120.45",
            "device_fingerprint": "a1b2c3d4e1b2c3d4e5f6a1b2c5f6a3d4",
            "customer_country": "RUS",
        },
    },
]


def main() -> None:
    client = httpx.Client(timeout=TIMEOUT)

    for scenario in SCENARIOS:
        print(f"\n{'='*60}")
        print(f"  {scenario['label']}")
        print(f"  withdrawal_id: {scenario['body']['withdrawal_id']}")
        print(f"{'='*60}")

        try:
            resp = client.post(
                f"{BASE}/api/withdrawals/investigate",
                json=scenario["body"],
            )
            resp.raise_for_status()
            data = resp.json()
            print(f"  Decision : {data.get('decision')}")
            print(f"  Risk     : {data.get('risk_score')} ({data.get('risk_percent')}%)")
            print(f"  Summary  : {data.get('summary')}")
            print(f"  Elapsed  : {data.get('total_elapsed_s', data.get('elapsed_s', 'N/A'))}s")

            triage = data.get("triage", {})
            if triage.get("elapsed_s", 0) > 0:
                print(f"  Triage   : {triage.get('constellation_analysis', 'N/A')[:100]}...")

            print(f"\n  Indicators:")
            for ind in data.get("indicators", []):
                print(f"    {ind['display_name']:25s} score={ind['score']:.2f}  {ind['reasoning'][:60]}...")

        except httpx.HTTPStatusError as e:
            print(f"  ERROR {e.response.status_code}: {e.response.text[:500]}")
        except httpx.RequestError as e:
            print(f"  REQUEST ERROR: {e}")

    client.close()


if __name__ == "__main__":
    main()

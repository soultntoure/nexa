"""Stress test the Nexa agent with edge cases and complex queries.

Sends 12 challenging queries to test:
- Complex aggregations
- NULL handling
- Edge cases (division by zero, empty sets)
- Ambiguous natural language
- Statistical calculations
"""

import asyncio
import json
import time
from datetime import datetime

import httpx


BASE_URL = "http://localhost:18080"

TEST_QUERIES = [
    {
        "id": 1,
        "query": "Show me customers who have made withdrawals but never used a VPN, including their total withdrawal amount and device count",
        "category": "Complex Multi-Table Aggregation with NULL Handling",
        "expected_issues": ["NULL handling in LEFT JOIN", "BOOL_OR logic for VPN detection"],
    },
    {
        "id": 2,
        "query": "Calculate the average withdrawal amount per customer, but only for customers who have at least one withdrawal, and show their approval rate (approved withdrawals / total withdrawals)",
        "category": "Division by Zero Edge Case",
        "expected_issues": ["Division by zero", "NULL handling in decimals"],
    },
    {
        "id": 3,
        "query": "Show me all the suspicious activity from last month",
        "category": "Ambiguous Time Reference",
        "expected_issues": ["'Last month' interpretation", "'Suspicious activity' definition"],
    },
    {
        "id": 4,
        "query": "Find customers who have more than 3 withdrawals, an average withdrawal over $500, AND at least one flagged transaction",
        "category": "Complex HAVING with Multiple Conditions",
        "expected_issues": ["HAVING vs WHERE", "JOIN to withdrawal_decisions"],
    },
    {
        "id": 5,
        "query": "What's the average number of withdrawals per customer, grouped by country?",
        "category": "Nested Aggregation",
        "expected_issues": ["AVG of COUNT", "Requires CTE or subquery"],
    },
    {
        "id": 6,
        "query": "Find customers whose names contain 'Ahmed' or 'Hassan' (case insensitive)",
        "category": "String Matching Edge Case",
        "expected_issues": ["ILIKE vs LIKE", "Pattern construction"],
    },
    {
        "id": 7,
        "query": "Find pairs of customers who share the same IP address AND the same device fingerprint",
        "category": "Self-Join Comparison",
        "expected_issues": ["Self-join", "Avoiding duplicate pairs", "Multiple criteria"],
    },
    {
        "id": 8,
        "query": "Show me customers whose total withdrawal amount is in the top 10% of all customers",
        "category": "Percentile Calculation",
        "expected_issues": ["PERCENTILE_CONT or window functions"],
    },
    {
        "id": 9,
        "query": "Do customers who use VPNs have higher withdrawal amounts on average?",
        "category": "Misleading Correlation",
        "expected_issues": ["Comparative analysis", "VPN vs non-VPN groups"],
    },
    {
        "id": 10,
        "query": "Rank customers by their total withdrawal amount and show the top 5 with their rank",
        "category": "Window Function with Ranking",
        "expected_issues": ["ROW_NUMBER vs RANK", "Window functions"],
    },
    {
        "id": 11,
        "query": "Show me all customers who made withdrawals on February 1st, 2020",
        "category": "Empty Set Handling",
        "expected_issues": ["Empty result set", "Agent should acknowledge"],
    },
    {
        "id": 12,
        "query": "Find blocked withdrawals that were approved",
        "category": "Contradictory Filters",
        "expected_issues": ["Logically impossible", "Agent should recognize contradiction"],
    },
]


async def send_query(client: httpx.AsyncClient, query: str) -> dict:
    """Send query to chat endpoint and collect full response."""
    response_data = {
        "sql_query": None,
        "answer": "",
        "tools_used": [],
        "ttft": None,
        "total_time": None,
        "error": None,
    }

    start_time = time.time()
    first_token_time = None

    try:
        async with client.stream(
            "POST",
            f"{BASE_URL}/api/query/chat",
            json={"question": query, "history": []},
            timeout=60.0,
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue

                try:
                    event = json.loads(line[6:])
                    event_type = event.get("type")

                    if event_type == "tool_start" and event.get("name") == "sql_db_query":
                        response_data["sql_query"] = event.get("preview", "")[:500]

                    elif event_type == "token":
                        if first_token_time is None:
                            first_token_time = time.time()
                        response_data["answer"] += event.get("content", "")

                    elif event_type == "answer":
                        response_data["answer"] = event.get("content", "")

                    elif event_type == "done":
                        response_data["tools_used"] = event.get("tools_used", [])

                    elif event_type == "error":
                        response_data["error"] = event.get("message", "Unknown error")

                except json.JSONDecodeError:
                    continue

        end_time = time.time()
        response_data["total_time"] = end_time - start_time
        response_data["ttft"] = (
            first_token_time - start_time if first_token_time else None
        )

    except Exception as e:
        response_data["error"] = str(e)
        response_data["total_time"] = time.time() - start_time

    return response_data


async def run_stress_test():
    """Run all stress tests and save results."""
    print("🧪 Starting Nexa Agent Stress Test")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔗 Target: {BASE_URL}")
    print(f"📊 Total Tests: {len(TEST_QUERIES)}\n")

    results = []

    async with httpx.AsyncClient() as client:
        for i, test in enumerate(TEST_QUERIES, 1):
            print(f"[{i}/{len(TEST_QUERIES)}] Testing: {test['category']}")
            print(f"   Query: {test['query'][:60]}...")

            response = await send_query(client, test["query"])

            result = {
                "test_id": test["id"],
                "category": test["category"],
                "query": test["query"],
                "expected_issues": test["expected_issues"],
                "sql_query": response["sql_query"],
                "answer": response["answer"],
                "tools_used": response["tools_used"],
                "ttft": response["ttft"],
                "total_time": response["total_time"],
                "error": response["error"],
                "timestamp": datetime.now().isoformat(),
            }

            results.append(result)

            if response["error"]:
                print(f"   ❌ Error: {response['error']}")
            else:
                print(f"   ✅ Completed in {response['total_time']:.2f}s")

            # Rate limiting
            await asyncio.sleep(2)

    # Save results
    output_file = f"outputs/stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Stress test complete! Results saved to {output_file}")

    # Summary
    passed = sum(1 for r in results if not r["error"])
    failed = len(results) - passed
    print(f"\n📊 Summary:")
    print(f"   Passed: {passed}/{len(results)}")
    print(f"   Failed: {failed}/{len(results)}")
    print(f"   Success Rate: {passed/len(results)*100:.1f}%")

    return results


if __name__ == "__main__":
    asyncio.run(run_stress_test())

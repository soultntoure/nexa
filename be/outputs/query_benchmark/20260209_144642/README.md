# Query Endpoint Benchmark Results — Feb 9, 2026

## Quick Summary

```
KEYWORD ENDPOINT (/api/query)
├─ Avg Latency:  0.295s  ⚡
├─ Success Rate: 100%    ✓
├─ Use Case:     Simple filters, dashboards, reports
└─ Cost:         $0/query (no LLM calls)

CHAT ENDPOINT (/api/query/chat)
├─ Avg Latency:  4.135s  🤔
├─ Avg TTFT:     3.791s
├─ Success Rate: 100%    ✓
├─ Use Case:     Complex analytics, ad-hoc queries
└─ Cost:         ~4 tokens/query
```

---

## Files in This Directory

| File | Description |
|------|-------------|
| `keyword_benchmark.csv` | 20 keyword endpoint queries (10 questions × 2 iterations) |
| `chat_benchmark.csv` | 30 chat streaming queries (15 questions × 2 iterations) |
| `summary.txt` | Aggregate statistics (latency, TTFT, success rate) |
| `ANALYSIS.md` | **Full analysis** with optimization recommendations |
| `README.md` | This file (quick reference) |

---

## Performance Comparison

### Latency Distribution

```
Keyword Endpoint (0.25s - 0.41s)
▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
 0s              0.5s              1s              1.5s

Chat Endpoint (2.43s - 8.31s)
░░░░░░░░░░░░░░░░░░░░░░▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
 0s              2s              4s              6s              8s
```

### Speed Comparison

| Query Type | Keyword | Chat | Winner |
|------------|---------|------|--------|
| Simple count | 0.27s | 2.5s | **Keyword (9x)** |
| Filtered list | 0.29s | 3.2s | **Keyword (11x)** |
| Aggregation | 0.31s | 3.3s | **Keyword (11x)** |
| Multi-table join | N/A | 5.8s | Chat only |
| Analytics | N/A | 8.2s | Chat only |

---

## Sample Questions

### Keyword Endpoint (Fast)

✓ "Show me all blocked transactions" — **0.31s**
✓ "What's the auto-approval rate?" — **0.29s**
✓ "Show high risk transactions" — **0.31s**
✓ "Show me escalated withdrawals" — **0.29s**
✓ "Show transactions by country" — **0.27s**

### Chat Endpoint (Flexible)

✓ "How many customers blocked in last 24h?" — **2.5s**
✓ "Show withdrawals over $5000 with risk scores" — **3.5s**
✓ "Average withdrawal amount by decision type" — **3.3s**
✓ "Find customers sharing device fingerprint" — **5.8s**
✓ "Correlation between velocity and fraud" — **8.2s**

---

## Key Metrics

| Metric | Keyword | Chat |
|--------|---------|------|
| **P50 latency** | 0.29s | 3.2s |
| **P95 latency** | 0.41s | 7.9s |
| **TTFT** | N/A | 3.8s |
| **Success rate** | 100% | 100% |
| **Tokens/query** | 0 | 4.3 |
| **Token throughput** | N/A | 1.1 tok/s |

---

## When to Use Each

### Use Keyword Endpoint When:
- ✅ Query matches pre-defined patterns
- ✅ Need sub-second response (<0.5s)
- ✅ Building dashboards/widgets
- ✅ High-frequency polling
- ✅ Mobile/low-bandwidth clients

### Use Chat Endpoint When:
- ✅ Complex analytical questions
- ✅ Multi-table JOINs required
- ✅ Ad-hoc analyst investigations
- ✅ Natural language UI needed
- ✅ Acceptable to wait 2-8s

---

## Next Steps

See **ANALYSIS.md** for:
- Detailed performance breakdown by query complexity
- Optimization recommendations (caching, parallelization)
- Production readiness assessment
- Query-by-query results

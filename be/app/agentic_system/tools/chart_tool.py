"""LLM-callable tool for rendering charts in the chat UI."""

import json
import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def render_chart(
    title: str,
    chart_type: str,
    x_key: str,
    series: list[dict],
    rows: list[dict],
) -> str:
    """Render a chart in the chat UI. Call this AFTER getting SQL results when the data is suitable for visualization.

    Args:
        title: Short chart title (max 60 chars).
        chart_type: One of "bar", "line", "pie".
        x_key: The key in each row dict used for x-axis labels.
        series: List of {"key": "<row_key>", "label": "<display_label>"} for y-axis metrics.
        rows: List of dicts with the data. Each dict must contain x_key and all series keys.

    Returns:
        Confirmation message.

    Example — "Top 5 customers by withdrawal amount":
        render_chart(
            title="Top 5 Customers by Withdrawal Amount",
            chart_type="bar",
            x_key="customer",
            series=[{"key": "total_amount", "label": "Total Amount"}],
            rows=[
                {"customer": "James Wilson", "total_amount": 150779.16},
                {"customer": "Raj Patel", "total_amount": 52009.80},
                {"customer": "Sophie Laurent", "total_amount": 29396.48},
            ]
        )

    Guidelines:
        - Use "bar" for ranked lists, comparisons, top-N.
        - Use "line" for time series (dates on x-axis).
        - Use "pie" for part-to-whole with ≤8 slices.
        - Max 24 rows. If more, take top/bottom N.
        - x_key values should be short labels (truncate if needed).
        - series values must be numeric.
    """
    if chart_type not in ("bar", "line", "pie"):
        return f"Error: chart_type must be bar, line, or pie. Got: {chart_type}"
    if not rows:
        return "Error: rows is empty, nothing to chart."
    if not series:
        return "Error: series is empty, no metrics to plot."
    if len(rows) > 100:
        return "Error: too many rows (max 100). Limit your query."

    chart_spec = {
        "__chart__": True,
        "title": title[:60],
        "chart_type": chart_type,
        "x_key": x_key,
        "series": series,
        "rows": rows[:100],
        "meta": {
            "reason": "llm_tool_call",
            "confidence": 0.95,
            "source": "llm_tool",
        },
    }
    return json.dumps(chart_spec)

# SSE Event Contract

Server-Sent Events emitted by `POST /api/query/chat`.

**Format**: `data: {"type": "event_type", ...payload...}\n\n`

---

## Event Lifecycle

```mermaid
flowchart TD
    START[Stream opens] --> STATUS[status: Thinking...]

    STATUS --> TOOL_LOOP{Agent calls tool?}
    TOOL_LOOP -->|sql_db_query| TS[tool_start: SQL preview]
    TS --> TE[tool_end: SQL result]
    TE --> TOOL_LOOP

    TOOL_LOOP -->|render_chart| RC[chart: LLM-generated chart data]
    RC --> TOOL_LOOP

    TOOL_LOOP -->|No more tools| TOKEN_LOOP[token: streaming text chunks]
    TOKEN_LOOP --> TOKEN_LOOP

    TOKEN_LOOP -->|Stream complete| FALLBACK{chart_emitted?}
    FALLBACK -->|No + SQL data exists| DET_CHART[chart: deterministic fallback]
    FALLBACK -->|Yes or no data| ANSWER[answer: full assembled text]
    DET_CHART --> ANSWER

    ANSWER --> DONE[done: tools_used list]

    ERR[error: failure message]
    TOOL_LOOP -.->|Exception| ERR
    TOKEN_LOOP -.->|Exception| ERR

    classDef required fill:#7ED321,stroke:#333,stroke-width:2px,color:#000
    classDef optional fill:#F5A623,stroke:#333,stroke-width:2px,color:#000
    classDef error fill:#E74C3C,stroke:#333,stroke-width:2px,color:#000

    class STATUS,ANSWER,DONE required
    class TS,TE,RC,DET_CHART,TOKEN_LOOP optional
    class ERR error
```

**Green** = always emitted | **Orange** = conditional | **Red** = error path

---

## Event Sequence (Typical Query with Chart)

```mermaid
sequenceDiagram
    participant SVC as streaming_service
    participant FE as Frontend

    SVC-->>FE: {type: "status", message: "Thinking..."}
    SVC-->>FE: {type: "tool_start", name: "sql_db_query", preview: "SELECT ..."}
    SVC-->>FE: {type: "tool_end", name: "sql_db_query", result: "country | count..."}
    SVC-->>FE: {type: "chart", chart: {title, chart_type, rows, meta}}
    SVC-->>FE: {type: "token", content: "Based"}
    SVC-->>FE: {type: "token", content: " on the data..."}
    SVC-->>FE: {type: "answer", content: "Based on the data..."}
    SVC-->>FE: {type: "done", tools_used: ["sql_db_query", "render_chart"]}
```

---

## Event Sequence (Text-Only, No Chart)

```mermaid
sequenceDiagram
    participant SVC as streaming_service
    participant FE as Frontend

    SVC-->>FE: {type: "status", message: "Thinking..."}
    SVC-->>FE: {type: "tool_start", name: "sql_db_query", preview: "SELECT ..."}
    SVC-->>FE: {type: "tool_end", name: "sql_db_query", result: "count: 42"}
    SVC-->>FE: {type: "token", content: "There"}
    SVC-->>FE: {type: "token", content: " are 42 ..."}
    SVC-->>FE: {type: "answer", content: "There are 42 ..."}
    SVC-->>FE: {type: "done", tools_used: ["sql_db_query"]}
```

---

## Event Sequence (Error with Partial Answer)

```mermaid
sequenceDiagram
    participant SVC as streaming_service
    participant FE as Frontend

    SVC-->>FE: {type: "status", message: "Thinking..."}
    SVC-->>FE: {type: "tool_start", name: "sql_db_query", preview: "SELECT ..."}
    SVC-->>FE: {type: "token", content: "Based on"}
    Note over SVC: Exception occurs
    SVC-->>FE: {type: "answer", content: "Based on"}
    SVC-->>FE: {type: "error", message: "Query failed: ..."}
```

---

## Event Types Reference

### `status`

Emitted immediately on stream open.

| Field | Type | Example |
|-------|------|---------|
| `type` | `"status"` | `"status"` |
| `message` | `string` | `"Thinking..."` |

**Client**: Show thinking spinner, disable input.

### `tool_start`

Agent begins a tool call (SQL query or chart render).

| Field | Type | Example |
|-------|------|---------|
| `type` | `"tool_start"` | `"tool_start"` |
| `name` | `string` | `"sql_db_query"` |
| `preview` | `string` (max 500 chars) | `"SELECT country, COUNT(*)..."` |

**Client**: Show SQL preview / loading indicator.

### `tool_end`

Tool call returns a result.

| Field | Type | Example |
|-------|------|---------|
| `type` | `"tool_end"` | `"tool_end"` |
| `name` | `string` | `"sql_db_query"` |
| `result` | `string` (max 2000 chars) | `"country \| count\nUS \| 45"` |

**Client**: Optionally display raw results, prepare for chart.

### `token`

LLM streams a text chunk (token-by-token).

| Field | Type | Example |
|-------|------|---------|
| `type` | `"token"` | `"token"` |
| `content` | `string` | `"Based"` |

**Client**: Append to answer text in real-time.

### `chart`

Chart data ready for rendering. Two sources:

| Source | `meta.reason` | When |
|--------|--------------|------|
| LLM tool call | `"llm_tool_call"` | Agent explicitly calls `render_chart` |
| Deterministic fallback | `"deterministic"` | Post-stream, SQL data is chartable but LLM didn't chart |

**Payload schema**:

| Field | Type | Description |
|-------|------|-------------|
| `type` | `"chart"` | |
| `chart.title` | `string` (max 60) | Chart title |
| `chart.chart_type` | `"bar" \| "line" \| "pie"` | Visualization type |
| `chart.x_key` | `string` | Row key for x-axis labels |
| `chart.series` | `Array<{key, label}>` | Metrics to plot |
| `chart.rows` | `Array<Record<string, number \| string>>` | 1-100 data points |
| `chart.meta` | `{reason, confidence, source}` | Generation metadata |

**Chart type selection**:

```mermaid
flowchart LR
    DATA[SQL Result] --> CHECK{Data shape?}
    CHECK -->|Ranked list / categories| BAR[bar]
    CHECK -->|Date on x-axis / trends| LINE[line]
    CHECK -->|Part-to-whole, ≤8 slices| PIE[pie]
```

**Client**: Parse config, extract labels from `rows[*][x_key]`, plot each series, render inline.

### `answer`

Full assembled answer text (concatenation of all tokens).

| Field | Type | Example |
|-------|------|---------|
| `type` | `"answer"` | `"answer"` |
| `content` | `string` | `"Based on the data, the US leads..."` |

**Client**: Lock answer display, finalize formatting.

### `done`

Stream complete, no more events.

| Field | Type | Example |
|-------|------|---------|
| `type` | `"done"` | `"done"` |
| `tools_used` | `string[]` | `["sql_db_query", "render_chart"]` |

**Client**: Hide spinner, enable input, log telemetry.

### `error`

Stream failed (may follow partial `answer`).

| Field | Type | Example |
|-------|------|---------|
| `type` | `"error"` | `"error"` |
| `message` | `string` | `"Query failed: Column 'x' does not exist"` |

**Client**: Show error banner, optionally retry with modified question.

---

## Client Receiver Workflow

```mermaid
flowchart TD
    READ[Read SSE chunk from stream] --> PARSE[Split by newlines, find data: lines]
    PARSE --> JSON[JSON.parse event]
    JSON --> SWITCH{event.type?}

    SWITCH -->|status| SPINNER[Show thinking spinner]
    SWITCH -->|tool_start| PREVIEW[Show SQL preview]
    SWITCH -->|tool_end| RAW[Optionally show raw result]
    SWITCH -->|token| APPEND[Append to answer text]
    SWITCH -->|chart| RENDER[Render chart inline]
    SWITCH -->|answer| FINALIZE[Lock answer display]
    SWITCH -->|done| COMPLETE[Hide spinner, enable input]
    SWITCH -->|error| ERROR[Show error banner]

    SPINNER --> READ
    PREVIEW --> READ
    RAW --> READ
    APPEND --> READ
    RENDER --> READ
    FINALIZE --> READ
    COMPLETE --> END[Stream closed]
    ERROR --> END
```

---

## Performance

| Metric | Value |
|--------|-------|
| Time to first `token` | ~2.9s |
| Time between tokens | 50-100ms |
| Total stream duration | 3-5s |
| Max events per stream | ~50-100 |

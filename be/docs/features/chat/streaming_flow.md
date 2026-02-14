# Analyst Chat: Streaming Flow

Complete client-to-API-to-client flow with chart generation.

## High-Level Workflow

```mermaid
flowchart TD
    CLIENT[Client: POST /api/query/chat] --> ROUTE[Route: query.py]
    ROUTE --> STREAM[stream_analyst_answer]

    STREAM --> INIT{Agent initialized?}
    INIT -->|No| BUILD[init_analyst_agent — once at startup]
    INIT -->|Yes| STATUS[Yield SSE: status — Thinking...]
    BUILD --> STATUS

    STATUS --> CONFIG[Configure thread_id = session_id]
    CONFIG --> LOOP[astream_events loop]

    LOOP --> EVT{Event type?}
    EVT -->|on_tool_start| TS[Yield SSE: tool_start + SQL preview]
    EVT -->|on_tool_end: sql_db_query| TE[Yield SSE: tool_end + result]
    EVT -->|on_tool_end: render_chart| CHART_LLM[Yield SSE: chart — LLM path]
    EVT -->|on_chat_model_stream| TOK[Buffer token parts]
    EVT -->|on_chat_model_end| EMIT{Has tool calls?}

    EMIT -->|Yes| LOOP
    EMIT -->|No| TOKENS[Yield SSE: token per buffered part]
    TOKENS --> LOOP

    TS --> LOOP
    TE --> LOOP
    CHART_LLM --> LOOP

    LOOP -->|Stream done| FALLBACK{Chart emitted?}
    FALLBACK -->|No + SQL output exists| DET[Deterministic chart fallback]
    FALLBACK -->|Yes or no data| ANSWER[Yield SSE: answer — full text]
    DET -->|Chart built| CHART_DET[Yield SSE: chart — deterministic]
    DET -->|No chart| ANSWER
    CHART_DET --> ANSWER

    ANSWER --> DONE[Yield SSE: done + tools_used]

    classDef client fill:#7ED321,stroke:#333,stroke-width:2px,color:#000
    classDef service fill:#F5A623,stroke:#333,stroke-width:2px,color:#000
    classDef event fill:#4A90E2,stroke:#333,stroke-width:2px,color:#000
    classDef chart fill:#BD10E0,stroke:#333,stroke-width:2px,color:#000

    class CLIENT,ROUTE client
    class STREAM,BUILD,CONFIG,LOOP service
    class TS,TE,TOK,TOKENS,ANSWER,DONE,STATUS event
    class CHART_LLM,CHART_DET,DET chart
```

---

## Agent Initialization (Singleton)

```mermaid
sequenceDiagram
    participant Main as app/main.py
    participant SS as streaming_service.py
    participant DB as PostgreSQL
    participant GM as Gemini API

    Note over Main: Called ONCE at startup
    Main->>SS: init_analyst_agent()
    SS->>DB: Query information_schema
    DB-->>SS: Table/column metadata
    SS->>SS: build_schema_description() + build_critical_notes()
    SS->>SS: create_sql_toolkit(sync_uri, llm)
    SS->>SS: Filter to sql_db_query + render_chart tools
    SS->>SS: Inject schema docs into ANALYST_CHAT_PROMPT
    SS->>SS: create_agent(llm, tools, prompt, InMemorySaver)

    Main->>SS: warmup_analyst_agent()
    SS->>GM: Fire cheap query (pre-warm LLM + SQL pool)
    GM-->>SS: OK

    Note over SS: Agent singleton ready for all requests
```

**Key decisions**:
- Schema is pre-injected into prompt (saves ~2s per query by avoiding `sql_db_schema` / `sql_db_list_tables` tool calls)
- Only `sql_db_query` + `render_chart` tools exposed
- `InMemorySaver` checkpointer preserves conversation history server-side via `thread_id`

---

## Streaming Request (Happy Path — with Chart)

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as query.py route
    participant SVC as streaming_service
    participant Agent as LangChain Agent
    participant SQL as PostgreSQL
    participant GM as Gemini 2.5 Flash

    FE->>API: POST /api/query/chat {question, session_id}
    API->>SVC: stream_analyst_answer(question, session_id)
    SVC-->>FE: SSE: {type: "status", message: "Thinking..."}

    SVC->>Agent: astream_events({messages: [user question]}, thread_id)

    Agent->>GM: Plan: which tools to use?
    GM-->>Agent: Call sql_db_query

    Agent->>SVC: event: on_tool_start(sql_db_query)
    SVC-->>FE: SSE: {type: "tool_start", preview: "SELECT ..."}

    Agent->>SQL: Execute SQL query
    SQL-->>Agent: Result rows

    Agent->>SVC: event: on_tool_end(sql_db_query)
    SVC-->>FE: SSE: {type: "tool_end", result: "country | count | ..."}

    Agent->>GM: Reason about results, decide to chart
    GM-->>Agent: Call render_chart

    Agent->>SVC: event: on_tool_end(render_chart)
    SVC-->>FE: SSE: {type: "chart", chart: {title, chart_type, rows, ...}}

    Agent->>GM: Generate text answer
    GM-->>Agent: Streaming tokens

    loop Token by token
        Agent->>SVC: event: on_chat_model_stream(chunk)
        SVC-->>FE: SSE: {type: "token", content: "..."}
    end

    Agent->>SVC: event: on_chat_model_end
    SVC-->>FE: SSE: {type: "answer", content: "full assembled text"}
    SVC-->>FE: SSE: {type: "done", tools_used: ["sql_db_query", "render_chart"]}
```

---

## Deterministic Chart Fallback

```mermaid
sequenceDiagram
    participant SVC as streaming_service
    participant Builder as charting/builder.py
    participant FE as Frontend

    Note over SVC: Stream done, chart_emitted == false, last_sql_output exists

    SVC->>Builder: build_chart(question, sql_output, sql_query, force=True)
    Builder->>Builder: parse_sql_tool_output() — raw string → list[dict]
    Builder->>Builder: profile_columns() — identify numeric vs categorical
    Builder->>Builder: check_suitability() — validate chartable data
    Builder->>Builder: choose_chart_type() — bar / line / pie

    alt Chart is suitable
        Builder-->>SVC: ChartSpec
        SVC-->>FE: SSE: {type: "chart", chart: {..., meta: {reason: "deterministic"}}}
    else Not chartable
        Builder-->>SVC: None
        Note over SVC: No chart emitted, answer-only response
    end
```

---

## Error Handling Flow

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant SVC as streaming_service
    participant Agent as LangChain Agent

    SVC->>Agent: astream_events(...)

    alt Agent raises exception
        Agent--xSVC: Exception
        SVC->>SVC: Assemble partial answer from buffered tokens
        opt Partial answer exists
            SVC-->>FE: SSE: {type: "answer", content: "partial text..."}
        end
        SVC-->>FE: SSE: {type: "error", message: "Query failed: ..."}
    end

    alt render_chart parse error
        Agent->>SVC: on_tool_end(render_chart) with malformed JSON
        SVC->>SVC: Log warning, skip chart
        Note over SVC: Continues streaming, no chart emitted
    end

    alt Deterministic fallback error
        SVC->>SVC: build_chart() raises exception
        SVC->>SVC: Log warning, skip chart
        Note over SVC: Answer sent without visualization (graceful degradation)
    end
```

---

## History Management

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant SVC as streaming_service
    participant CP as InMemorySaver

    FE->>SVC: question="Show top 5 countries", session_id="user-123"
    SVC->>CP: Store under thread_id="user-123"
    SVC-->>FE: Answer about top 5 countries

    FE->>SVC: question="Now show it as a trend", session_id="user-123"
    SVC->>CP: Load thread_id="user-123" — full prior context available
    Note over SVC: Agent sees previous question + answer + SQL results
    SVC-->>FE: Answer with time-series trend

    FE->>SVC: question="Unrelated query", session_id="user-456"
    SVC->>CP: New thread_id="user-456" — no prior context
    SVC-->>FE: Fresh answer
```

Multi-turn conversations work seamlessly. No client-side history needed.

---

## Key Files

| File | Purpose |
|------|---------|
| `app/api/routes/query.py` | Route handler, returns `StreamingResponse` |
| `app/services/chat/streaming_service.py` | `init_analyst_agent()` singleton + `stream_analyst_answer()` SSE generator |
| `app/agentic_system/prompts/analyst_chat.py` | System prompt template |
| `app/agentic_system/tools/sql/schema_builder.py` | Live schema generation from `information_schema` |
| `app/agentic_system/tools/sql/toolkit.py` | SQL toolkit factory + tool filtering |
| `app/agentic_system/tools/chart_tool.py` | `render_chart` tool for LLM |
| `app/services/chat/charting/builder.py` | Deterministic chart builder fallback |
| `nexa-fe/pages/query.vue` | Frontend SSE receiver + chart renderer |

## Performance (Feb 2026)

| Phase | Duration | % of Total |
|-------|----------|-----------|
| Agent planning + tool selection | 0.2s | 5% |
| SQL execution | 2.4s | 65% |
| LLM reasoning + streaming | 0.8s | 22% |
| Chart generation (if applicable) | 0.3s | 8% |
| **TOTAL** | **3.7s** | **100%** |

**TTFT**: ~2.9s | **Throughput**: 1.1 tokens/sec | **Accuracy**: 100% (12/12 stress tests)

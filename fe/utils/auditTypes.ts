export interface Phase {
  name: string
  label: string
  status: 'pending' | 'active' | 'completed'
  detail: string | null
  startedAt: string | null
  duration: number | null
}

export interface ToolCall {
  tool: string
  friendlyLabel: string
  narration: string | null
  timestamp: string
  kind: 'tool' | 'insight'
}

export interface ClusterStep {
  clusterId: string
  label: string
  status: 'pending' | 'active' | 'completed'
  eventCount: number
  accountCount: number
  sourceType: string
  toolCalls: ToolCall[]
  patternName: string | null
}

export interface SqlFinding {
  query?: string
  result?: string
  insight?: string
  query_summary?: string
  result_summary?: string
  source?: string
}

export interface WebReference {
  title?: string
  url?: string
  snippet?: string
  relevance?: string
}

export interface EvidenceUnit {
  source?: string
  source_name?: string
  source_type?: string
  text?: string
  text_preview?: string
  confidence?: number
  score?: number
  rank_score?: number
  withdrawal_id?: string
  type?: string
  summary?: string
  result?: string
  query?: string
  snippet?: string
  evidence_type?: string
  rank?: number
  unit_id?: string
}

export interface PatternCard {
  formal_pattern_name?: string
  plain_language?: string
  analyst_notes?: string
  limitations?: string
  uncertainty?: string
  clustering_notes?: string
  sql_findings?: SqlFinding[]
  web_references?: WebReference[]
  evidence_units?: EvidenceUnit[]
  ranked_evidence?: EvidenceUnit[]
  tool_trace?: Record<string, unknown>[]
  source_types?: string[]
  support_accounts?: number
  [key: string]: unknown
}

export interface CandidateResult {
  candidate_id: string
  title: string | null
  status: string
  quality_score: number
  confidence: number
  support_events: number
  support_accounts?: number
  novelty_status: string
  pattern_card: PatternCard
}

export interface AuditState {
  runId: string | null
  status: 'idle' | 'streaming' | 'completed' | 'error'
  phases: Phase[]
  clusters: ClusterStep[]
  candidates: CandidateResult[]
  selectedClusterId: string | null
  selectedCandidateId: string | null
  error: string | null
}

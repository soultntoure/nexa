import { $fetch } from 'ofetch'
import { ref, shallowRef } from 'vue'

import type { AuditState, CandidateResult, ClusterStep, Phase } from '../utils/auditTypes'
import { createEventHandlers } from './useAuditEventHandlers'

interface TriggerRunResponse {
  run_id: string
  status?: string
}

interface RunStatusResponse {
  run_id: string
  status: string
  error_message?: string | null
}

interface CandidateListResponse {
  candidates: CandidateResult[]
}

interface SSEEventPayload {
  type: string
  phase?: string | null
  title: string
  detail?: string | null
  narration?: string | null
  progress?: number | null
  metadata?: Record<string, unknown>
  timestamp: string
}

const PHASES: Array<{ name: string, label: string }> = [
  { name: 'extract', label: 'Scanning Transactions' },
  { name: 'embed_cluster', label: 'Grouping Patterns' },
  { name: 'investigate', label: 'Deep-Dive Analysis' },
  { name: 'artifacts', label: 'Compiling Report' },
]

const STREAM_EVENT_TYPES = ['phase_start', 'progress', 'hypothesis', 'agent_tool', 'insight', 'candidate', 'complete', 'error'] as const

function buildInitialPhases(): Phase[] {
  return PHASES.map(phase => ({
    name: phase.name,
    label: phase.label,
    status: 'pending',
    detail: null,
    startedAt: null,
    duration: null,
  }))
}

function toErrorMessage(err: unknown, fallback: string): string {
  if (typeof err === 'string' && err) return err
  if (err && typeof err === 'object') {
    const maybeData = (err as { data?: { detail?: string }, message?: string })
    if (maybeData.data?.detail) return maybeData.data.detail
    if (maybeData.message) return maybeData.message
  }
  return fallback
}

function parseSSEPayload(data: string, fallbackType: string): SSEEventPayload | null {
  try {
    const parsed = JSON.parse(data) as Partial<SSEEventPayload>
    if (!parsed || typeof parsed !== 'object') return null

    return {
      type: String(parsed.type || fallbackType),
      phase: parsed.phase ?? null,
      title: String(parsed.title || fallbackType),
      detail: parsed.detail ?? null,
      narration: (parsed as Record<string, unknown>).narration as string | null ?? null,
      progress: parsed.progress ?? null,
      metadata: parsed.metadata ?? {},
      timestamp: String(parsed.timestamp || new Date().toISOString()),
    }
  } catch {
    return null
  }
}

// ── Module-scope singleton state ──────────────────────────────────
const runId = ref<string | null>(null)
const status = ref<AuditState['status']>('idle')
const phases = ref<Phase[]>(buildInitialPhases())
const clusters = ref<ClusterStep[]>([])
const candidates = ref<CandidateResult[]>([])
const selectedClusterId = ref<string | null>(null)
const selectedCandidateId = ref<string | null>(null)
const error = ref<string | null>(null)
const clusterToCandidateMap = ref<Record<string, string>>({})
const activeClusterRef = { value: null as ClusterStep | null }
const eventSource = shallowRef<EventSource | null>(null)

const handlers = createEventHandlers(
  phases, clusters, candidates, status, error,
  selectedClusterId, clusterToCandidateMap, runId, activeClusterRef,
)

// ── Internal helpers (module-scope) ───────────────────────────────
function closeStream(): void {
  if (!eventSource.value) return
  eventSource.value.close()
  eventSource.value = null
}

function resetState(): void {
  phases.value = buildInitialPhases()
  clusters.value = []
  candidates.value = []
  selectedClusterId.value = null
  selectedCandidateId.value = null
  error.value = null
  clusterToCandidateMap.value = {}
  activeClusterRef.value = null
}

function markAllPhasesCompleted(detail: string): void {
  const completedAt = new Date().toISOString()
  for (const phase of phases.value) {
    phase.status = 'completed'
    phase.detail = phase.detail || detail
    phase.startedAt = phase.startedAt || completedAt
    phase.duration = phase.duration ?? 0
  }
}

function dispatchEvent(event: SSEEventPayload): void {
  switch (event.type) {
    case 'phase_start':
      handlers.onPhaseStart(event)
      break
    case 'progress':
      handlers.onProgress(event)
      break
    case 'hypothesis':
      handlers.onHypothesis(event)
      break
    case 'agent_tool':
      handlers.onAgentTool(event)
      break
    case 'insight':
      handlers.onInsight(event)
      break
    case 'candidate':
      handlers.onCandidate(event)
      break
    case 'complete':
      void handlers.onComplete().finally(() => closeStream())
      break
    case 'error':
      handlers.onError(event)
      closeStream()
      break
    default:
      break
  }
}

function openStream(targetRunId: string): void {
  if (typeof window === 'undefined') return

  closeStream()
  const source = new EventSource(`/api/background-audits/runs/${targetRunId}/stream`)
  eventSource.value = source

  for (const eventType of STREAM_EVENT_TYPES) {
    source.addEventListener(eventType, (event: Event) => {
      const message = event as MessageEvent
      const parsed = parseSSEPayload(String(message.data || ''), eventType)
      if (!parsed) return
      dispatchEvent(parsed)
    })
  }

  source.onerror = () => {
    if (status.value === 'streaming') {
      status.value = 'error'
      error.value = error.value || 'Audit stream disconnected'
    }
    closeStream()
  }
}

// ── Public composable ─────────────────────────────────────────────
export function useAuditStream() {
  async function triggerRun(lookbackDays = 7): Promise<void> {
    closeStream()
    resetState()
    status.value = 'streaming'

    try {
      const response = await $fetch<TriggerRunResponse>('/api/background-audits/trigger', {
        method: 'POST',
        body: {
          lookback_days: lookbackDays,
          run_mode: 'full',
        },
      })

      runId.value = response.run_id
      openStream(response.run_id)
    } catch (err) {
      status.value = 'error'
      error.value = toErrorMessage(err, 'Failed to start audit run')
    }
  }

  async function loadPastRun(targetRunId: string): Promise<void> {
    closeStream()
    resetState()
    runId.value = targetRunId

    try {
      const run = await $fetch<RunStatusResponse>(`/api/background-audits/runs/${targetRunId}`)
      if (run.status === 'running' || run.status === 'pending') {
        status.value = 'streaming'
        openStream(targetRunId)
        return
      }

      if (run.status === 'failed') {
        status.value = 'error'
        error.value = run.error_message || 'Audit run failed'
        return
      }

      const response = await $fetch<CandidateListResponse>(`/api/background-audits/runs/${targetRunId}/candidates`)
      candidates.value = response.candidates || []
      markAllPhasesCompleted('Loaded from past run')
      status.value = 'completed'
    } catch (err) {
      status.value = 'error'
      error.value = toErrorMessage(err, 'Failed to load run data')
    }
  }

  function selectCluster(clusterId: string): void {
    selectedClusterId.value = clusterId
    const mappedCandidate = clusterToCandidateMap.value[clusterId]
    if (mappedCandidate) {
      selectedCandidateId.value = mappedCandidate
    }
  }

  function selectCandidate(candidateId: string): void {
    selectedCandidateId.value = candidateId
    const pair = Object.entries(clusterToCandidateMap.value).find(([, id]) => id === candidateId)
    if (pair) {
      selectedClusterId.value = pair[0]
    }
  }

  function reset(): void {
    closeStream()
    runId.value = null
    status.value = 'idle'
    resetState()
  }

  return {
    runId,
    status,
    phases,
    clusters,
    candidates,
    selectedClusterId,
    selectedCandidateId,
    error,
    triggerRun,
    loadPastRun,
    selectCluster,
    selectCandidate,
    reset,
  }
}

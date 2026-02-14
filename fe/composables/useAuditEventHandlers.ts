import type { Ref } from 'vue'
import type { Phase, ClusterStep, CandidateResult, AuditState } from '~/utils/auditTypes'

interface SSEEvent {
  type: string
  phase?: string | null
  title: string
  detail?: string | null
  narration?: string | null
  progress?: number | null
  metadata?: Record<string, unknown>
  timestamp: string
}

const TOOL_LABELS: Record<string, () => string> = {
  'sql_db_query': () => 'Querying the database...',
  'tavily_search_results_json': () => 'Searching for known fraud patterns...',
  'fraud_web_search': () => 'Searching for known fraud patterns...',
  'kmeans_cluster': () => 'Re-analyzing cluster structure...',
  'AgentSynthesisResult': () => 'Compiling findings...',
}

const PHASE_ORDER = ['extract', 'embed_cluster', 'investigate', 'artifacts'] as const

export function createEventHandlers(
  phases: Ref<Phase[]>,
  clusters: Ref<ClusterStep[]>,
  candidates: Ref<CandidateResult[]>,
  status: Ref<AuditState['status']>,
  error: Ref<string | null>,
  selectedClusterId: Ref<string | null>,
  clusterToCandidateMap: Ref<Record<string, string>>,
  runId: Ref<string | null>,
  activeClusterRef: { value: ClusterStep | null },
) {
  function getPhaseIndex(phaseName: string | null | undefined): number {
    if (!phaseName) return -1
    return PHASE_ORDER.indexOf(phaseName as typeof PHASE_ORDER[number])
  }

  function completePhase(phase: Phase, completedAt: string, fallbackDetail?: string): void {
    if (phase.status === 'completed') return
    phase.status = 'completed'
    if (!phase.detail && fallbackDetail) {
      phase.detail = fallbackDetail
    }
    if (phase.startedAt && phase.duration == null) {
      phase.duration = (new Date(completedAt).getTime() - new Date(phase.startedAt).getTime()) / 1000
    }
  }

  function completeMissingPreviousPhases(currentPhaseName: string | null | undefined, timestamp: string): void {
    const currentIdx = getPhaseIndex(currentPhaseName)
    if (currentIdx <= 0) return

    for (const phase of phases.value) {
      const idx = getPhaseIndex(phase.name)
      if (idx >= 0 && idx < currentIdx && phase.status !== 'completed') {
        completePhase(phase, timestamp, getAutoPhaseDetail(phase.name))
      }
    }
  }

  function ensureInvestigateActive(timestamp: string): void {
    completeMissingPreviousPhases('investigate', timestamp)

    const investigate = phases.value.find(p => p.name === 'investigate')
    if (!investigate) return
    if (investigate.status === 'pending') {
      investigate.status = 'active'
      investigate.startedAt = timestamp
    }
  }

  function getAutoPhaseDetail(phaseName: string): string {
    switch (phaseName) {
      case 'extract':
        return 'Extraction complete'
      case 'embed_cluster':
        return 'Clustering complete'
      case 'investigate':
        return 'Investigation complete'
      case 'artifacts':
        return 'Artifacts queued'
      default:
        return 'Completed'
    }
  }

  function onPhaseStart(e: SSEEvent): void {
    completeMissingPreviousPhases(e.phase, e.timestamp)

    for (const p of phases.value) {
      if (p.status === 'active' && p.name !== e.phase) {
        completePhase(p, e.timestamp, getAutoPhaseDetail(p.name))
      }
    }

    const phase = phases.value.find(p => p.name === e.phase)
    if (phase) {
      phase.status = 'active'
      phase.startedAt = e.timestamp
    }
  }

  function onProgress(e: SSEEvent): void {
    completeMissingPreviousPhases(e.phase, e.timestamp)

    const phase = phases.value.find(p => p.name === e.phase)
    if (!phase) return

    phase.status = 'completed'
    phase.detail = e.detail || getAutoPhaseDetail(phase.name)
    if (phase.startedAt) {
      phase.duration = (new Date(e.timestamp).getTime() - new Date(phase.startedAt).getTime()) / 1000
    }
  }

  function onHypothesis(e: SSEEvent): void {
    ensureInvestigateActive(e.timestamp)

    const m = e.metadata || {}
    const sourceTypes = Array.isArray(m.source_types)
      ? m.source_types.map(v => String(v))
      : Array.isArray(m.sources)
        ? m.sources.map(v => String(v))
        : []

    const c: ClusterStep = {
      clusterId: String(m.cluster_id || clusters.value.length),
      label: e.narration || e.title, status: 'active',
      eventCount: Number(m.event_count || m.unit_count || 0),
      accountCount: Number(m.account_count || 0),
      sourceType: sourceTypes.join(',') || 'unknown',
      toolCalls: [],
      patternName: null,
    }
    clusters.value.push(c)
    activeClusterRef.value = c
    selectedClusterId.value = c.clusterId
  }

  function onAgentTool(e: SSEEvent): void {
    ensureInvestigateActive(e.timestamp)

    if (!activeClusterRef.value) return
    const toolName = String(e.metadata?.tool_name || e.metadata?.tool || e.title)
    const narration = e.narration || null
    const friendlyLabel = narration || TOOL_LABELS[toolName]?.() || e.title

    activeClusterRef.value.toolCalls.push({
      tool: toolName, friendlyLabel, narration, timestamp: e.timestamp, kind: 'tool',
    })
  }

  function onInsight(e: SSEEvent): void {
    ensureInvestigateActive(e.timestamp)

    if (!activeClusterRef.value) return
    const narration = e.narration || e.title
    activeClusterRef.value.toolCalls.push({
      tool: 'insight',
      friendlyLabel: narration,
      narration,
      timestamp: e.timestamp,
      kind: 'insight',
    })
  }

  function onCandidate(e: SSEEvent): void {
    ensureInvestigateActive(e.timestamp)

    const m = e.metadata || {}
    const clusterId = String(m.cluster_id || '')
    const candidateId = String(m.candidate_id || '')
    const cluster = clusters.value.find(c => c.clusterId === clusterId)
    if (cluster) {
      cluster.status = 'completed'
      cluster.patternName = (m.pattern_name as string) || null
      cluster.eventCount = Number(m.event_count || m.unit_count || cluster.eventCount)
      cluster.accountCount = Number(m.account_count || cluster.accountCount)
    }
    if (candidateId && clusterId) {
      clusterToCandidateMap.value[clusterId] = candidateId
    }
    if (activeClusterRef.value?.clusterId === clusterId) {
      activeClusterRef.value = null
    }
  }

  async function onComplete(): Promise<void> {
    const completedAt = new Date().toISOString()

    for (const phase of phases.value) {
      if (phase.status !== 'completed') {
        completePhase(phase, completedAt, getAutoPhaseDetail(phase.name))
      }
    }

    for (const cluster of clusters.value) {
      if (cluster.status === 'active') {
        cluster.status = 'completed'
      }
    }
    activeClusterRef.value = null

    status.value = 'completed'
    if (!runId.value) return
    try {
      const r = await $fetch<{ candidates: CandidateResult[] }>(
        `/api/background-audits/runs/${runId.value}/candidates`,
      )
      candidates.value = r.candidates || []
    } catch { /* keep empty */ }
  }

  function onError(e: SSEEvent): void {
    status.value = 'error'
    error.value = e.detail || 'Unknown error occurred'
  }

  return {
    onPhaseStart, onProgress, onHypothesis, onAgentTool, onInsight, onCandidate, onComplete, onError,
  }
}

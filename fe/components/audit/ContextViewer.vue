<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { CandidateResult, ClusterStep } from '~/utils/auditTypes'

interface Props {
  selectedCluster: ClusterStep | null
  selectedCandidate: CandidateResult | null
  status: string
}

const props = defineProps<Props>()

type TabName = 'summary' | 'evidence' | 'sql' | 'web'

const activeTab = ref<TabName>('summary')

type GenericRecord = Record<string, unknown>

const evidenceItems = computed(() => {
  const candidate = props.selectedCandidate
  if (!candidate) return []

  const card = (candidate.pattern_card || {}) as GenericRecord
  const rankedEvidence = Array.isArray(card.ranked_evidence) ? card.ranked_evidence : []
  const generatedEvidence = (Array.isArray(card.evidence_units) ? card.evidence_units : [])
    .filter((item): item is GenericRecord => {
      if (!item || typeof item !== 'object') return false
      const type = String(item.type ?? item.source ?? '').toLowerCase()
      return !type.includes('sql_trace') && !type.includes('web_trace')
    })

  const raw = rankedEvidence.length > 0 ? rankedEvidence : generatedEvidence

  const normalized = raw
    .filter((item): item is GenericRecord => !!item && typeof item === 'object')
    .map((item) => {
      const rank = Number(item.rank)
      const fallbackConfidence = Number.isFinite(rank)
        ? Math.max(0.2, 1 - (Math.max(rank, 1) - 1) * 0.15)
        : 0.5

      return {
        source: String(item.source_name ?? item.source_type ?? item.source ?? item.type ?? item.evidence_type ?? 'evidence'),
        text: String(item.text ?? item.snippet ?? item.text_preview ?? item.summary ?? item.result ?? item.query ?? '').trim(),
        confidence: Number(item.confidence ?? fallbackConfidence),
        withdrawal_id: String(item.withdrawal_id ?? item.unit_id ?? ''),
        evidence_id: String(item.unit_id ?? ''),
      }
    })
    .filter(item => item.text.length > 0)

  const seen = new Set<string>()
  return normalized.filter((item) => {
    const key = item.evidence_id || `${item.source}|${item.text}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
})

const tabs = computed(() => {
  const candidate = props.selectedCandidate
  if (!candidate) return [{ name: 'summary' as TabName, label: 'Summary', icon: 'lucide:file-text', show: true }]

  return [
    { name: 'summary' as TabName, label: 'Summary', icon: 'lucide:file-text', show: true },
    {
      name: 'evidence' as TabName,
      label: 'Evidence',
      icon: 'lucide:list',
      show: evidenceItems.value.length > 0,
    },
    {
      name: 'sql' as TabName,
      label: 'SQL Findings',
      icon: 'lucide:database',
      show: (candidate.pattern_card.sql_findings?.length ?? 0) > 0
    },
    {
      name: 'web' as TabName,
      label: 'Web Proof',
      icon: 'lucide:globe',
      show: (candidate.pattern_card.web_references?.length ?? 0) > 0
    },
  ].filter((tab) => tab.show)
})

watch(
  () => props.selectedCandidate,
  () => {
    activeTab.value = 'summary'
  }
)
</script>

<template>
  <div class="h-full flex flex-col">
    <div v-if="selectedCandidate" class="flex-1 flex flex-col">
      <div class="border-b border-gray-200 px-5 pt-4">
        <div class="flex gap-4">
          <button
            v-for="tab in tabs"
            :key="tab.name"
            type="button"
            class="flex items-center gap-1.5 pb-3 px-2 text-sm font-medium transition-colors"
            :class="
              activeTab === tab.name
                ? 'border-b-2 border-primary-500 text-primary-600'
                : 'text-gray-500 hover:text-gray-700'
            "
            @click="activeTab = tab.name"
          >
            <Icon :icon="tab.icon" class="h-4 w-4" />
            <span>{{ tab.label }}</span>
          </button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-5">
        <AuditPatternCard v-if="activeTab === 'summary'" :candidate="selectedCandidate" />
        <AuditEvidenceExplorer
          v-else-if="activeTab === 'evidence'"
          :evidence="evidenceItems"
        />
        <AuditSqlFindings v-else-if="activeTab === 'sql'" :findings="selectedCandidate.pattern_card.sql_findings ?? []" />
        <AuditWebReferences
          v-else-if="activeTab === 'web'"
          :references="selectedCandidate.pattern_card.web_references ?? []"
        />
      </div>
    </div>

    <div v-else-if="status === 'streaming' && selectedCluster" class="flex-1 flex flex-col p-5">
      <div class="flex items-center gap-2 mb-1">
        <Icon icon="lucide:brain" class="h-5 w-5 text-primary-500 animate-pulse" />
        <h3 class="text-sm font-semibold text-gray-700">Agent Investigation</h3>
      </div>
      <p v-if="selectedCluster.toolCalls.length === 0" class="text-xs text-gray-400 mb-4">
        Starting analysis...
      </p>
      <div class="space-y-3 mt-3">
        <div
          v-for="(call, idx) in selectedCluster.toolCalls"
          :key="idx"
          class="flex items-start gap-3 text-sm"
          :class="call.kind === 'insight'
            ? 'bg-emerald-50 border border-emerald-200 rounded-lg p-3'
            : 'text-gray-600'"
        >
          <Icon
            :icon="call.kind === 'insight'
              ? 'lucide:lightbulb'
              : call.tool.includes('web') || call.tool.includes('tavily')
                ? 'lucide:globe'
                : call.tool.includes('cluster') || call.tool.includes('kmeans')
                  ? 'lucide:git-branch'
                  : 'lucide:database'"
            class="h-4 w-4 flex-shrink-0 mt-0.5"
            :class="call.kind === 'insight' ? 'text-emerald-600' : 'text-gray-400'"
          />
          <div class="flex-1 min-w-0">
            <span
              class="leading-relaxed"
              :class="call.kind === 'insight' ? 'text-emerald-700 font-medium' : ''"
            >
              {{ call.friendlyLabel }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="selectedCluster && status === 'completed'" class="flex-1 flex items-center justify-center p-8 text-center">
      <div>
        <Icon icon="lucide:info" class="mx-auto h-12 w-12 text-gray-300 mb-3" />
        <p class="text-sm text-gray-500">This cluster was filtered out or did not produce a candidate pattern</p>
      </div>
    </div>

    <div v-else class="flex-1 flex items-center justify-center p-8 text-center">
      <div>
        <Icon icon="lucide:circle-dashed" class="mx-auto h-12 w-12 text-gray-300 mb-3" />
        <p class="text-sm text-gray-500">Select a cluster from the timeline to see details</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { friendlySourceLabel } from '~/utils/auditHelpers'
import type { ClusterStep } from '~/utils/auditTypes'

interface Props {
  cluster: ClusterStep
  isSelected: boolean
}

interface Emits {
  (e: 'click'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const isInvestigating = computed(() =>
  props.cluster.status === 'active' && props.cluster.toolCalls.length > 0
)

const statusIcon = computed(() => {
  if (props.cluster.status === 'completed')
    return { icon: 'lucide:check-circle', class: 'text-green-500' }
  if (isInvestigating.value)
    return { icon: 'lucide:loader', class: 'text-primary-500 animate-spin' }
  if (props.cluster.status === 'active')
    return { icon: 'lucide:clock', class: 'text-amber-500' }
  return { icon: 'lucide:circle', class: 'text-gray-400' }
})

const SOURCE_ICONS: Record<string, { icon: string; label: string }> = {
  constellation_analysis: { icon: 'lucide:orbit', label: 'Multi-signal analysis' },
  identity_access: { icon: 'lucide:fingerprint', label: 'Identity & Access' },
  financial_behavior: { icon: 'lucide:trending-up', label: 'Financial Behavior' },
  cross_account: { icon: 'lucide:users', label: 'Cross-Account Links' },
}

const clusterIcon = computed(() => {
  // sourceType can be comma-separated like "cross_account,constellation_analysis"
  const sources = props.cluster.sourceType.split(',').map(s => s.trim())
  for (const src of sources) {
    if (SOURCE_ICONS[src]) return SOURCE_ICONS[src]
  }
  return { icon: 'lucide:search', label: 'Pattern Analysis' }
})

const friendlyLabel = computed(() => {
  const sources = props.cluster.sourceType.split(',').map(s => s.trim())
  if (sources.length === 1 && SOURCE_ICONS[sources[0]]) {
    return SOURCE_ICONS[sources[0]].label
  }
  return sources
    .map(s => SOURCE_ICONS[s]?.label || friendlySourceLabel(s))
    .join(' + ')
})

function getToolIcon(toolName: string): string {
  const lower = toolName.toLowerCase()
  if (lower.includes('sql') || lower.includes('db')) return 'lucide:database'
  if (lower.includes('web') || lower.includes('search')) return 'lucide:globe'
  if (lower.includes('cluster') || lower.includes('kmeans')) return 'lucide:git-branch'
  return 'lucide:file-text'
}

const containerClass = computed(() => {
  const base = 'cursor-pointer rounded-lg p-3 transition-all hover:bg-gray-50'
  if (props.isSelected) {
    return `${base} border-l-2 border-primary-500 bg-primary-50/50`
  }
  if (isInvestigating.value) {
    return `${base} border-l-2 border-primary-300`
  }
  if (props.cluster.status === 'active') {
    return `${base} border-l-2 border-amber-300`
  }
  return `${base} border-l-2 border-transparent`
})
</script>

<template>
  <div
    :class="containerClass"
    @click="emit('click')"
  >
    <div class="flex items-start gap-3">
      <Icon
        :icon="statusIcon.icon"
        :class="statusIcon.class"
        class="h-4 w-4 flex-shrink-0"
      />

      <div class="flex-1 space-y-2">
        <div class="flex items-center gap-2">
          <Icon
            :icon="clusterIcon.icon"
            class="h-4 w-4 text-gray-600"
          />
          <span class="text-sm font-medium text-gray-900">
            {{ friendlyLabel }}
          </span>
        </div>

        <div class="text-xs text-gray-400">
          {{ cluster.eventCount }} events, {{ cluster.accountCount }} accounts
        </div>

        <div
          v-if="cluster.status === 'active' && cluster.toolCalls.length > 0"
          class="space-y-1.5"
        >
          <div
            v-for="(call, idx) in cluster.toolCalls"
            :key="idx"
            class="flex items-start gap-2 text-xs"
            :class="call.kind === 'insight' ? 'text-emerald-600 font-medium' : 'text-gray-500'"
          >
            <Icon
              :icon="call.kind === 'insight' ? 'lucide:lightbulb' : getToolIcon(call.tool)"
              class="h-3 w-3 flex-shrink-0 mt-0.5"
              :class="call.kind === 'insight' ? 'text-emerald-500' : ''"
            />
            <span class="leading-snug">{{ call.friendlyLabel }}</span>
          </div>
        </div>

        <div
          v-if="cluster.status === 'completed' && cluster.patternName"
          class="inline-flex items-center rounded-full bg-primary-50 px-2 py-0.5 text-xs text-primary-700"
        >
          {{ cluster.patternName }}
        </div>
      </div>
    </div>
  </div>
</template>

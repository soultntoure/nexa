<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { CandidateResult } from '~/utils/auditTypes'
import { useDriftActions } from '~/composables/useDriftActions'

const props = defineProps<{
  driftCandidates: CandidateResult[]
  runId: string
}>()

const { isApplied, dismissAction } = useDriftActions()

const patternCard = computed(() => props.driftCandidates[0]?.pattern_card as Record<string, any> | undefined)
const drift = computed(() => patternCard.value?.drift_data as Record<string, any> | undefined)
const indicators = computed(() => (drift.value?.indicators ?? []) as any[])
const outliers = computed(() => (drift.value?.outliers ?? []) as any[])
const countermeasures = computed(() => (drift.value?.countermeasures ?? []) as any[])
const chartData = computed(() => drift.value?.chart_data ?? { labels: [], multipliers: [], trends: [] })
const totalRecalibrations = computed(() => drift.value?.total_recalibrations ?? 0)
const agentRecommendations = computed(() => (patternCard.value?.recommendations ?? []) as any[])
const currentConfig = computed(() => patternCard.value?.current_config as Record<string, any> | undefined)

const analysisWindow = computed(() => {
  if (!drift.value?.window_start || !drift.value?.window_end) return null
  const fmt = (d: string) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  return { start: fmt(drift.value.window_start), end: fmt(drift.value.window_end) }
})

const topDrifting = computed(() => {
  if (!indicators.value.length) return null
  return [...indicators.value].sort((a, b) => b.std - a.std)[0] ?? null
})

const showExplainer = ref(false)

function severityColor(s: string): string {
  return s === 'high' ? 'bg-red-100 text-red-700' : s === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'
}

function severityLabel(s: string): string {
  return s === 'high' ? 'Needs attention' : s === 'medium' ? 'Worth reviewing' : 'Low risk'
}

</script>

<template>
  <div v-if="drift" class="mt-6 rounded-xl border border-indigo-200 bg-white p-5">
    <!-- Header -->
    <div class="mb-4 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <Icon icon="lucide:activity" class="h-5 w-5 text-indigo-600" />
        <h2 class="text-lg font-semibold text-gray-900">Fraud Signal Health Check</h2>
        <span v-if="countermeasures.length" class="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
          {{ countermeasures.length }} {{ countermeasures.length === 1 ? 'issue' : 'issues' }} found
        </span>
      </div>
      <div v-if="analysisWindow" class="flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5">
        <Icon icon="lucide:calendar-range" class="h-4 w-4 text-indigo-500" />
        <span class="text-xs font-medium text-indigo-700">
          {{ analysisWindow.start }} — {{ analysisWindow.end }}
        </span>
      </div>
    </div>

    <!-- Explainer -->
    <div class="mb-4 rounded-lg border border-indigo-100 bg-indigo-50/50">
      <button
        class="flex w-full items-center justify-between px-3 py-2.5 text-left"
        @click="showExplainer = !showExplainer"
      >
        <div class="flex items-center gap-2">
          <Icon icon="lucide:help-circle" class="h-4 w-4 text-indigo-500" />
          <span class="text-sm text-indigo-700">What is this analysis?</span>
        </div>
        <Icon :icon="showExplainer ? 'lucide:chevron-up' : 'lucide:chevron-down'" class="h-4 w-4 text-indigo-400" />
      </button>
      <div v-if="showExplainer" class="border-t border-indigo-100 px-3 pb-3 pt-2">
        <p class="text-sm text-gray-600 leading-relaxed">
          Each customer has a set of fraud signals (e.g. identity mismatch, unusual amounts) that carry different weights.
          Over time, these weights get adjusted automatically based on new data. This analysis checks whether those
          adjustments have drifted too far — meaning some signals may be over- or under-influencing fraud decisions.
          Think of it as a calibration check for the fraud detection system.
        </p>
      </div>
    </div>

    <!-- Summary Cards -->
    <div class="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div class="rounded-lg border border-gray-100 bg-gray-50 p-3 text-center">
        <div class="text-2xl font-bold text-gray-900">{{ totalRecalibrations }}</div>
        <div class="text-xs text-gray-500">Weight adjustments</div>
      </div>
      <div class="rounded-lg border border-gray-100 bg-gray-50 p-3 text-center">
        <div class="text-2xl font-bold text-gray-900">{{ indicators.length }}</div>
        <div class="text-xs text-gray-500">Signals tracked</div>
      </div>
      <div class="rounded-lg border border-gray-100 bg-gray-50 p-3 text-center">
        <div class="text-2xl font-bold" :class="outliers.length > 0 ? 'text-orange-600' : 'text-gray-900'">{{ outliers.length }}</div>
        <div class="text-xs text-gray-500">Customers affected</div>
      </div>
      <div class="rounded-lg border border-gray-100 bg-gray-50 p-3 text-center">
        <div class="truncate text-sm font-bold text-indigo-600">{{ topDrifting?.label ?? topDrifting?.name ?? 'None' }}</div>
        <div class="text-xs text-gray-500">Most shifted signal</div>
      </div>
    </div>

    <!-- Charts -->
    <AuditDriftCharts v-if="chartData.labels.length" :chart-data="chartData" class="mb-5" />

    <!-- Recommendations -->
    <div v-if="countermeasures.length" class="mb-5">
      <h3 class="mb-2 text-sm font-semibold text-gray-700">Recommendations</h3>
      <div class="space-y-2">
        <div
          v-for="(cm, i) in countermeasures"
          :key="i"
          class="flex items-start justify-between gap-3 rounded-lg border border-gray-100 bg-gray-50 px-4 py-3"
        >
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-sm font-medium text-gray-800">{{ cm.indicator_label ?? cm.indicator_name }}</span>
              <span :class="['rounded-full px-2 py-0.5 text-xs font-medium', severityColor(cm.severity)]">
                {{ severityLabel(cm.severity) }}
              </span>
            </div>
            <p class="text-sm text-gray-600">{{ cm.issue }}</p>
            <p class="text-xs text-gray-400 mt-0.5">{{ cm.suggestion }}</p>
          </div>
          <div class="shrink-0 pt-1">
            <div v-if="isApplied(`dismiss:${cm.indicator_name}`)" class="flex items-center gap-1 text-green-600 text-xs">
              <Icon icon="lucide:check" class="h-4 w-4" /> Dismissed
            </div>
            <button
              v-else
              class="rounded bg-gray-200 px-2.5 py-1 text-xs text-gray-600 hover:bg-gray-300"
              @click="dismissAction(`dismiss:${cm.indicator_name}`)"
            >
              Dismiss
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Agent Recommendations -->
    <div v-if="agentRecommendations.length" class="mb-5">
      <h3 class="mb-2 text-sm font-semibold text-gray-700">Agent Recommendations</h3>
      <div class="space-y-2">
        <div
          v-for="(rec, i) in agentRecommendations"
          :key="i"
          class="rounded-lg border border-indigo-100 bg-indigo-50/40 px-4 py-3"
        >
          <div class="flex items-center gap-2 mb-1">
            <Icon icon="lucide:lightbulb" class="h-4 w-4 text-indigo-500" />
            <span class="text-sm font-medium text-gray-800">{{ rec.action }}</span>
            <span :class="['rounded-full px-2 py-0.5 text-xs font-medium', rec.priority === 'high' ? 'bg-red-100 text-red-700' : rec.priority === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700']">
              {{ rec.priority }}
            </span>
          </div>
          <p class="text-sm text-gray-600">Target: {{ rec.target }}</p>
          <p class="text-xs text-gray-400 mt-0.5">{{ rec.reason }}</p>
        </div>
      </div>
    </div>

    <!-- Current Configuration -->
    <div v-if="currentConfig" class="mb-5">
      <h3 class="mb-2 text-sm font-semibold text-gray-700">Current System Configuration</h3>
      <div class="rounded-lg border border-gray-100 bg-gray-50 px-4 py-3">
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 mb-3">
          <div>
            <span class="text-xs text-gray-400">Approve threshold</span>
            <div class="text-sm font-medium text-gray-800">{{ (currentConfig.approve_threshold * 100).toFixed(0) }}%</div>
          </div>
          <div>
            <span class="text-xs text-gray-400">Block threshold</span>
            <div class="text-sm font-medium text-gray-800">{{ (currentConfig.block_threshold * 100).toFixed(0) }}%</div>
          </div>
        </div>
        <div>
          <span class="text-xs text-gray-400 mb-1 block">Baseline signal weights</span>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="(weight, name) in currentConfig.baseline_weights"
              :key="name"
              class="rounded-full border border-gray-200 bg-white px-2.5 py-1 text-xs text-gray-600"
            >
              {{ name }}: <span class="font-medium">{{ weight }}x</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

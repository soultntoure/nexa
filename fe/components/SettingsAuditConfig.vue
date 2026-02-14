<script setup lang="ts">
import { Icon } from '@iconify/vue'

const emit = defineEmits<{ saved: [] }>()

interface AuditConfig {
  id: string | null
  lookback_days: number
  max_candidates: number
  min_events: number
  min_accounts: number
  min_confidence: number
  output_dir: string
  updated_by: string
  reason: string | null
  is_active: boolean
  created_at: string | null
}

const isSaving = ref(false)
const isLoading = ref(true)
const historyOpen = ref(false)

const config = ref<AuditConfig>({
  id: null,
  lookback_days: 7,
  max_candidates: 50,
  min_events: 5,
  min_accounts: 2,
  min_confidence: 0.50,
  output_dir: 'outputs/background_audits/stage_1',
  updated_by: 'system',
  reason: null,
  is_active: true,
  created_at: null,
})

const changeReason = ref('')
const history = ref<AuditConfig[]>([])

const DEFAULTS: Omit<AuditConfig, 'id' | 'updated_by' | 'reason' | 'is_active' | 'created_at'> = {
  lookback_days: 7,
  max_candidates: 50,
  min_events: 5,
  min_accounts: 2,
  min_confidence: 0.50,
  output_dir: 'outputs/background_audits/stage_1',
}

async function loadConfig(): Promise<void> {
  isLoading.value = true
  try {
    const data = await $fetch<AuditConfig>('/api/background-audits/config')
    config.value = data
  } catch {
    // Use defaults
  }
  isLoading.value = false
}

async function loadHistory(): Promise<void> {
  try {
    const data = await $fetch<{ configs: AuditConfig[] }>('/api/background-audits/config/history?limit=10')
    history.value = data.configs
  } catch {
    history.value = []
  }
}

async function saveConfig(): Promise<void> {
  isSaving.value = true
  try {
    const data = await $fetch<AuditConfig>('/api/background-audits/config', {
      method: 'PUT',
      body: {
        lookback_days: config.value.lookback_days,
        max_candidates: config.value.max_candidates,
        min_events: config.value.min_events,
        min_accounts: config.value.min_accounts,
        min_confidence: config.value.min_confidence,
        output_dir: config.value.output_dir,
        updated_by: 'officer-demo-001',
        reason: changeReason.value || 'Updated via settings',
      },
    })
    config.value = data
    changeReason.value = ''
    emit('saved')
    await loadHistory()
  } catch {
    // Fallback for demo
  }
  isSaving.value = false
}

function resetDefaults(): void {
  Object.assign(config.value, DEFAULTS)
}

function formatDate(dateString: string | null): string {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function confidenceColor(val: number): string {
  if (val >= 0.7) return 'text-red-600'
  if (val >= 0.5) return 'text-amber-600'
  return 'text-green-600'
}

onMounted(async () => {
  await loadConfig()
  await loadHistory()
})

defineExpose({ save: saveConfig, resetDefaults, isSaving })
</script>

<template>
  <div class="space-y-6">
    <!-- Loading skeleton -->
    <div v-if="isLoading" class="flex items-center justify-center py-16">
      <Icon icon="lucide:loader-2" class="h-6 w-6 animate-spin text-gray-400" />
    </div>

    <template v-else>
      <!-- Scanning Window -->
      <div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div class="mb-4 flex items-center gap-2">
          <Icon icon="lucide:calendar-range" class="h-5 w-5 text-blue-600" />
          <h2 class="text-base font-semibold text-gray-900">Scanning Window</h2>
        </div>
        <p class="mb-4 text-sm text-gray-500">
          How far back the background audit looks when scanning transaction history for patterns.
        </p>

        <div class="rounded-lg bg-gray-50 p-4">
          <div class="flex items-center gap-4">
            <span class="w-10 text-sm font-medium text-gray-500">1d</span>
            <div class="flex-1">
              <input
                v-model.number="config.lookback_days"
                type="range"
                min="1"
                max="90"
                step="1"
                class="w-full accent-blue-600"
              />
            </div>
            <span class="w-10 text-sm font-medium text-gray-500">90d</span>
          </div>
          <div class="mt-2 flex items-center justify-center gap-2">
            <span class="text-2xl font-bold text-blue-700">{{ config.lookback_days }}</span>
            <span class="text-sm text-gray-400">days</span>
          </div>
          <p class="mt-1 text-center text-xs text-gray-400">
            Longer windows find more patterns but increase scan duration
          </p>
        </div>
      </div>

      <!-- Discovery Thresholds -->
      <div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div class="mb-4 flex items-center gap-2">
          <Icon icon="lucide:filter" class="h-5 w-5 text-gray-600" />
          <h2 class="text-base font-semibold text-gray-900">Discovery Thresholds</h2>
        </div>
        <p class="mb-4 text-sm text-gray-500">
          Minimum criteria a pattern must meet to be reported as a candidate.
          Higher values produce fewer, higher-quality candidates.
        </p>

        <div class="grid grid-cols-1 gap-5 sm:grid-cols-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Min Events</label>
            <input
              v-model.number="config.min_events"
              type="number"
              min="1"
              max="100"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500"
            />
            <p class="mt-1 text-xs text-gray-400">Minimum suspicious events in a cluster</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Min Accounts</label>
            <input
              v-model.number="config.min_accounts"
              type="number"
              min="1"
              max="50"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500"
            />
            <p class="mt-1 text-xs text-gray-400">Minimum accounts involved in a pattern</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Min Confidence</label>
            <div class="flex items-center gap-2">
              <input
                v-model.number="config.min_confidence"
                type="number"
                min="0"
                max="1"
                step="0.05"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500"
              />
              <span class="text-sm font-bold" :class="confidenceColor(config.min_confidence)">
                {{ (config.min_confidence * 100).toFixed(0) }}%
              </span>
            </div>
            <p class="mt-1 text-xs text-gray-400">Agent confidence threshold to surface a finding</p>
          </div>
        </div>
      </div>

      <!-- Output Limits -->
      <div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div class="mb-4 flex items-center gap-2">
          <Icon icon="lucide:box" class="h-5 w-5 text-gray-600" />
          <h2 class="text-base font-semibold text-gray-900">Output Limits</h2>
        </div>

        <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Max Candidates</label>
            <input
              v-model.number="config.max_candidates"
              type="number"
              min="1"
              max="500"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500"
            />
            <p class="mt-1 text-xs text-gray-400">Maximum patterns to report per audit run</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Output Directory</label>
            <input
              v-model="config.output_dir"
              type="text"
              class="w-full rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-sm font-mono text-gray-600 focus:border-primary-500 focus:ring-2 focus:ring-primary-500"
            />
            <p class="mt-1 text-xs text-gray-400">Where audit artifacts are saved on disk</p>
          </div>
        </div>
      </div>

      <!-- Change Reason -->
      <div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div class="mb-4 flex items-center gap-2">
          <Icon icon="lucide:message-square-text" class="h-5 w-5 text-gray-600" />
          <h2 class="text-base font-semibold text-gray-900">Change Reason</h2>
        </div>
        <input
          v-model="changeReason"
          type="text"
          placeholder="Why are you changing this config? (optional)"
          class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500"
        />
      </div>

      <!-- Version History -->
      <div class="rounded-xl border border-gray-200 bg-white shadow-sm">
        <button
          class="flex w-full items-center justify-between p-6"
          @click="historyOpen = !historyOpen"
        >
          <div class="flex items-center gap-2">
            <Icon icon="lucide:history" class="h-5 w-5 text-gray-600" />
            <h2 class="text-base font-semibold text-gray-900">Config History</h2>
            <span class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">{{ history.length }}</span>
          </div>
          <Icon
            icon="lucide:chevron-down"
            class="h-5 w-5 text-gray-400 transition-transform"
            :class="{ 'rotate-180': historyOpen }"
          />
        </button>

        <div v-if="historyOpen && history.length > 0" class="border-t border-gray-100 px-6 pb-4">
          <div class="mt-3 overflow-hidden rounded-lg border border-gray-100">
            <table class="w-full text-left text-sm">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-500">Date</th>
                  <th class="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-500">Lookback</th>
                  <th class="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-500">Candidates</th>
                  <th class="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-500">Confidence</th>
                  <th class="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-500">By</th>
                  <th class="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-500">Reason</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-50">
                <tr v-for="(entry, idx) in history" :key="entry.id ?? idx" class="hover:bg-gray-50">
                  <td class="whitespace-nowrap px-3 py-2 text-gray-600">{{ formatDate(entry.created_at) }}</td>
                  <td class="px-3 py-2 text-gray-700 font-medium">{{ entry.lookback_days }}d</td>
                  <td class="px-3 py-2 text-gray-700">{{ entry.max_candidates }}</td>
                  <td class="px-3 py-2">
                    <span :class="confidenceColor(entry.min_confidence)" class="font-medium">
                      {{ (entry.min_confidence * 100).toFixed(0) }}%
                    </span>
                  </td>
                  <td class="px-3 py-2 text-gray-500">{{ entry.updated_by }}</td>
                  <td class="max-w-[200px] truncate px-3 py-2 text-gray-400">{{ entry.reason || '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-if="historyOpen && history.length === 0" class="border-t border-gray-100 px-6 py-4">
          <p class="text-sm text-gray-400">No configuration changes recorded yet.</p>
        </div>
      </div>
    </template>
  </div>
</template>

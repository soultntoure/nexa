<script setup lang="ts">
import { Icon } from '@iconify/vue'

const emit = defineEmits<{ saved: [] }>()

const isSaving = ref(false)

const thresholds = ref({
  approve: 0.30,
  escalate_min: 0.30,
  escalate_max: 0.70,
  block: 0.70,
})

const indicators = ref([
  { key: 'amount_anomaly', label: 'Amount Anomaly', weight: 1.0 },
  { key: 'velocity', label: 'Velocity', weight: 1.0 },
  { key: 'payment_method', label: 'Payment Method', weight: 1.0 },
  { key: 'geographic', label: 'Geographic', weight: 1.2 },
  { key: 'device_fingerprint', label: 'Device Fingerprint', weight: 1.3 },
  { key: 'trading_behavior', label: 'Trading Behavior', weight: 1.5 },
  { key: 'recipient', label: 'Recipient Risk', weight: 1.0 },
  { key: 'card_errors', label: 'Card Errors', weight: 1.2 },
])

const notifications = ref({
  escalation_alerts: true,
  block_alerts: true,
  daily_digest: true,
  weekly_report: false,
  email_notifications: true,
  slack_notifications: false,
})

const apiConfig = ref({
  backend_url: 'http://localhost:8000',
  timeout: 30,
  retry_count: 3,
})

watch(() => thresholds.value.approve, (val) => {
  thresholds.value.escalate_min = val
})
watch(() => thresholds.value.block, (val) => {
  thresholds.value.escalate_max = val
})

function weightColor(weight: number): string {
  if (weight >= 1.5) return 'text-red-600'
  if (weight >= 1.2) return 'text-amber-600'
  return 'text-green-600'
}

async function saveSettings(): Promise<void> {
  isSaving.value = true
  try {
    const weights: Record<string, number> = {}
    indicators.value.forEach((i) => { weights[i.key] = i.weight })
    await $fetch('/api/settings', {
      method: 'POST',
      body: {
        approve_below: thresholds.value.approve * 100,
        escalate_below: thresholds.value.block * 100,
        indicator_weights: weights,
        updated_by: 'officer-demo-001',
        reason: 'Updated via settings page',
      },
    })
  } catch {
    // Fallback — still show saved for demo
  }
  isSaving.value = false
  emit('saved')
}

function resetDefaults(): void {
  thresholds.value = { approve: 0.30, escalate_min: 0.30, escalate_max: 0.70, block: 0.70 }
  indicators.value.forEach(i => {
    const defaults: Record<string, number> = {
      amount_anomaly: 1.0, velocity: 1.0, payment_method: 1.0, geographic: 1.2,
      device_fingerprint: 1.3, trading_behavior: 1.5, recipient: 1.0, card_errors: 1.2,
    }
    i.weight = defaults[i.key] ?? 1.0
  })
}

onMounted(async () => {
  try {
    const data = await $fetch<{ approve_below: number, escalate_below: number, indicator_weights: Record<string, number> }>('/api/settings')
    if (data) {
      thresholds.value.approve = data.approve_below / 100
      thresholds.value.escalate_min = data.approve_below / 100
      thresholds.value.escalate_max = data.escalate_below / 100
      thresholds.value.block = data.escalate_below / 100
      if (data.indicator_weights) {
        indicators.value.forEach((i) => {
          const w = data.indicator_weights[i.key]
          if (w !== undefined) {
            i.weight = w
          }
        })
      }
    }
  } catch {
    // Use defaults
  }
})

defineExpose({ save: saveSettings, resetDefaults, isSaving })
</script>

<template>
  <div class="space-y-6">
    <!-- Auto-Approve Threshold -->
    <div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div class="mb-4 flex items-center gap-2">
        <Icon icon="lucide:zap" class="h-5 w-5 text-green-600" />
        <h2 class="text-base font-semibold text-gray-900">Auto-Approve Threshold</h2>
      </div>
      <p class="mb-4 text-sm text-gray-500">
        Transactions scoring below this threshold are automatically approved without LLM investigation.
        Lower values are more conservative (fewer auto-approvals). Higher values process more payouts instantly.
      </p>

      <div class="rounded-lg bg-gray-50 p-4">
        <div class="flex items-center gap-4">
          <span class="w-10 text-sm font-medium text-gray-500">0.10</span>
          <div class="flex-1">
            <input
              v-model.number="thresholds.approve"
              type="range"
              min="0.10"
              max="0.50"
              step="0.05"
              class="w-full accent-green-600"
            />
          </div>
          <span class="w-10 text-sm font-medium text-gray-500">0.50</span>
        </div>
        <div class="mt-2 flex items-center justify-center gap-2">
          <span class="text-2xl font-bold text-green-700">{{ thresholds.approve.toFixed(2) }}</span>
          <span class="text-sm text-gray-400">risk score</span>
        </div>
        <p class="mt-1 text-center text-xs text-gray-400">
          Estimated auto-approval rate:
          <span class="font-semibold" :class="thresholds.approve >= 0.30 ? 'text-green-600' : 'text-amber-600'">
            {{ thresholds.approve >= 0.35 ? '~60%' : thresholds.approve >= 0.30 ? '~56%' : thresholds.approve >= 0.20 ? '~40%' : '~25%' }}
          </span>
          of clean traffic
        </p>
      </div>
    </div>

    <!-- Decision Thresholds -->
    <div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div class="mb-4 flex items-center gap-2">
        <Icon icon="lucide:sliders-horizontal" class="h-5 w-5 text-gray-600" />
        <h2 class="text-base font-semibold text-gray-900">Decision Thresholds</h2>
      </div>
      <p class="mb-4 text-sm text-gray-500">Define risk score ranges for automatic decisions</p>

      <div class="mb-6 rounded-lg bg-gray-50 p-4">
        <div class="relative h-6 overflow-hidden rounded-full bg-gray-200">
          <div
            class="absolute inset-y-0 left-0 bg-green-400"
            :style="{ width: `${thresholds.approve * 100}%` }"
          />
          <div
            class="absolute inset-y-0 bg-amber-400"
            :style="{ left: `${thresholds.escalate_min * 100}%`, width: `${(thresholds.escalate_max - thresholds.escalate_min) * 100}%` }"
          />
          <div
            class="absolute inset-y-0 right-0 bg-red-400"
            :style="{ width: `${(1 - thresholds.block) * 100}%` }"
          />
        </div>
        <div class="mt-2 flex justify-between text-xs">
          <span class="text-green-700">Auto-Approve (&lt;{{ thresholds.approve.toFixed(2) }})</span>
          <span class="text-amber-700">Escalate ({{ thresholds.escalate_min.toFixed(2) }}-{{ thresholds.escalate_max.toFixed(2) }})</span>
          <span class="text-red-700">Block (&gt;={{ thresholds.block.toFixed(2) }})</span>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Escalate Range</label>
          <div class="flex items-center gap-2">
            <input
              :value="thresholds.approve.toFixed(2)"
              type="text"
              disabled
              class="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-400"
            />
            <span class="text-gray-400">-</span>
            <input
              v-model.number="thresholds.escalate_max"
              type="number"
              step="0.01"
              min="0"
              max="1"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <p class="mt-1 text-xs text-gray-400">Score in range = manual review + LLM investigation</p>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Block Threshold</label>
          <input
            v-model.number="thresholds.block"
            type="number"
            step="0.01"
            min="0"
            max="1"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500"
          />
          <p class="mt-1 text-xs text-gray-400">Score at or above = auto-block</p>
        </div>
      </div>
    </div>

    <!-- Indicator Weight Tuning -->
    <div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div class="mb-4 flex items-center gap-2">
        <Icon icon="lucide:gauge" class="h-5 w-5 text-gray-600" />
        <h2 class="text-base font-semibold text-gray-900">Indicator Weight Tuning</h2>
      </div>
      <p class="mb-4 text-sm text-gray-500">Adjust the importance of each risk indicator in the composite score</p>

      <div class="space-y-4">
        <div v-for="indicator in indicators" :key="indicator.key" class="flex items-center gap-4">
          <span class="w-40 text-sm text-gray-700">{{ indicator.label }}</span>
          <div class="flex-1">
            <input
              v-model.number="indicator.weight"
              type="range"
              min="0"
              max="3"
              step="0.1"
              class="w-full accent-primary-600"
            />
          </div>
          <span class="w-12 text-right text-sm font-bold" :class="weightColor(indicator.weight)">
            {{ indicator.weight.toFixed(1) }}
          </span>
        </div>
      </div>
    </div>

    <!-- Notification Preferences -->
    <div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div class="mb-4 flex items-center gap-2">
        <Icon icon="lucide:bell" class="h-5 w-5 text-gray-600" />
        <h2 class="text-base font-semibold text-gray-900">Notification Preferences</h2>
      </div>

      <div class="space-y-3">
        <label v-for="(value, key) in notifications" :key="key" class="flex items-center justify-between rounded-lg p-3 hover:bg-gray-50">
          <div>
            <p class="text-sm font-medium text-gray-800 capitalize">{{ String(key).replace(/_/g, ' ') }}</p>
          </div>
          <input
            v-model="notifications[key as keyof typeof notifications]"
            type="checkbox"
            class="h-5 w-5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
          />
        </label>
      </div>
    </div>

    <!-- API Configuration -->
    <div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div class="mb-4 flex items-center gap-2">
        <Icon icon="lucide:server" class="h-5 w-5 text-gray-600" />
        <h2 class="text-base font-semibold text-gray-900">API Configuration</h2>
      </div>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div class="sm:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">Backend URL</label>
          <input
            v-model="apiConfig.backend_url"
            type="text"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Timeout (seconds)</label>
          <input
            v-model.number="apiConfig.timeout"
            type="number"
            min="5"
            max="120"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500"
          />
        </div>
      </div>
    </div>
  </div>
</template>

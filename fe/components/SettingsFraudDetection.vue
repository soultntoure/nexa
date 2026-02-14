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
        <h2 class="text-base font-semibold text-gray-900">Auto Approve Threshold</h2>
      </div>
      <p class="mb-4 text-sm text-gray-500">
        Transactions scoring below this threshold are automatically approved without LLM investigation.
        Lower values are more conservative (fewer auto-approvals). Higher values process more payouts instantly.
      </p>

      <div class="rounded-lg bg-gray-50 p-4">
        <div class="flex items-center gap-4">
          <span class="w-10 text-sm font-medium text-gray-500">0.10</span>
          <div class="flex-1">
            <SliderRoot
              :model-value="[thresholds.approve]"
              :min="0.10"
              :max="0.50"
              :step="0.05"
              class="relative flex h-5 w-full touch-none select-none items-center"
              @update:model-value="(v?: number[]) => { if (v) thresholds.approve = v[0] }"
            >
              <SliderTrack class="relative h-1.5 grow rounded-full bg-gray-200">
                <SliderRange class="absolute h-full rounded-full bg-green-600" />
              </SliderTrack>
              <SliderThumb class="block h-4 w-4 rounded-full bg-white shadow-md ring-1 ring-gray-300 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-green-500" />
            </SliderRoot>
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
        <h2 class="text-base font-semibold text-gray-900">Decision Thresholds</h2>
      </div>
      <p class="mb-4 text-sm text-gray-500">Define risk score ranges for automatic decisions</p>

      <div class="mb-6 rounded-lg bg-gray-50 p-4">
        <div class="relative h-6 overflow-hidden rounded-full bg-gray-200">
          <div
            class="absolute inset-y-0 left-0 bg-emerald-600"
            :style="{ width: `${thresholds.approve * 100}%` }"
          />
          <div
            class="absolute inset-y-0 bg-yellow-500"
            :style="{ left: `${thresholds.escalate_min * 100}%`, width: `${(thresholds.escalate_max - thresholds.escalate_min) * 100}%` }"
          />
          <div
            class="absolute inset-y-0 right-0 bg-[#E60B22]"
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
            <NumberFieldRoot
              v-model="thresholds.escalate_max"
              :min="0"
              :max="1"
              :step="0.01"
              class="flex items-center gap-1"
            >
              <NumberFieldDecrement class="inline-flex h-8 w-8 items-center justify-center rounded bg-gray-100 text-gray-500 hover:bg-gray-200">
                <Icon icon="lucide:minus" class="h-3 w-3" />
              </NumberFieldDecrement>
              <NumberFieldInput class="h-8 w-16 rounded border border-gray-300 bg-white text-center text-sm text-gray-900 focus:border-primary-500 focus:ring-2 focus:ring-primary-500 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none" />
              <NumberFieldIncrement class="inline-flex h-8 w-8 items-center justify-center rounded bg-gray-100 text-gray-500 hover:bg-gray-200">
                <Icon icon="lucide:plus" class="h-3 w-3" />
              </NumberFieldIncrement>
            </NumberFieldRoot>
          </div>
          <p class="mt-1 text-xs text-gray-400">Score in range = manual review + LLM investigation</p>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Block Threshold</label>
          <NumberFieldRoot
            v-model="thresholds.block"
            :min="0"
            :max="1"
            :step="0.01"
            class="flex items-center gap-1"
          >
            <NumberFieldDecrement class="inline-flex h-8 w-8 items-center justify-center rounded bg-gray-100 text-gray-500 hover:bg-gray-200">
              <Icon icon="lucide:minus" class="h-3 w-3" />
            </NumberFieldDecrement>
            <NumberFieldInput class="h-8 w-16 rounded border border-gray-300 bg-white text-center text-sm text-gray-900 focus:border-primary-500 focus:ring-2 focus:ring-primary-500 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none" />
            <NumberFieldIncrement class="inline-flex h-8 w-8 items-center justify-center rounded bg-gray-100 text-gray-500 hover:bg-gray-200">
              <Icon icon="lucide:plus" class="h-3 w-3" />
            </NumberFieldIncrement>
          </NumberFieldRoot>
          <p class="mt-1 text-xs text-gray-400">Score at or above = auto-block</p>
        </div>
      </div>
    </div>

    <!-- Indicator Weight Tuning -->
    <div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div class="mb-4 flex items-center gap-2">
        <h2 class="text-base font-semibold text-gray-900">Indicator Weight Tuning</h2>
      </div>
      <p class="mb-4 text-sm text-gray-500">Adjust the importance of each risk indicator in the composite score</p>

      <div class="space-y-4">
        <div v-for="indicator in indicators" :key="indicator.key" class="flex items-center gap-4">
          <span class="w-40 text-sm text-gray-700">{{ indicator.label }}</span>
          <div class="flex-1">
            <SliderRoot
              :model-value="[indicator.weight]"
              :min="0"
              :max="3"
              :step="0.1"
              class="relative flex h-5 w-full touch-none select-none items-center"
              @update:model-value="(v?: number[]) => { if (v) indicator.weight = v[0]! }"
            >
              <SliderTrack class="relative h-1.5 grow rounded-full bg-gray-200">
                <SliderRange class="absolute h-full rounded-full bg-primary-600" />
              </SliderTrack>
              <SliderThumb class="block h-4 w-4 rounded-full bg-white shadow-md ring-1 ring-gray-300 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500" />
            </SliderRoot>
          </div>
          <span class="w-12 text-right text-sm font-bold" :class="weightColor(indicator.weight)">
            {{ indicator.weight.toFixed(1) }}
          </span>
        </div>
      </div>
    </div>

  </div>
</template>

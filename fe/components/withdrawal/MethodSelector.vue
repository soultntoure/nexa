<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { WITHDRAWAL_METHODS, type WithdrawalMethod } from '~/composables/useWithdrawal'
import { formatCurrency } from '~/utils/formatters'

const selected = defineModel<WithdrawalMethod | null>('selected', { default: null })
</script>

<template>
  <div class="space-y-4">
    <h3 class="text-sm font-semibold text-gray-700">Select Withdrawal Method</h3>

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <button
        v-for="method in WITHDRAWAL_METHODS"
        :key="method.id"
        class="flex items-center gap-4 p-4 bg-white rounded-xl border-2 transition-all text-left"
        :class="selected?.id === method.id
          ? 'border-primary-500 bg-primary-50/30 shadow-sm'
          : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'"
        @click="selected = method"
      >
        <div
          class="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
          :class="selected?.id === method.id ? 'bg-primary-100' : 'bg-gray-100'"
        >
          <Icon
            :icon="method.icon"
            class="w-6 h-6"
            :class="selected?.id === method.id ? 'text-primary-600' : 'text-gray-500'"
          />
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-semibold text-gray-900">{{ method.name }}</p>
          <p class="text-xs text-gray-500 mt-0.5">{{ method.processingTime }}</p>
          <div class="flex items-center gap-3 mt-1 text-xs text-gray-400">
            <span>Fee: {{ method.fee }}</span>
            <span>Min: {{ formatCurrency(method.minAmount) }}</span>
          </div>
        </div>
        <div v-if="selected?.id === method.id">
          <Icon icon="lucide:check-circle-2" class="w-5 h-5 text-primary-600" />
        </div>
      </button>
    </div>

    <!-- Fraud Evaluation Info -->
    <div class="bg-amber-50 border border-amber-200 rounded-lg p-4">
      <div class="flex items-start gap-3">
        <Icon icon="lucide:shield-alert" class="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
        <div>
          <p class="text-sm font-medium text-amber-800">AI-Powered Fraud Evaluation</p>
          <p class="text-xs text-amber-700 mt-1 leading-relaxed">
            Every withdrawal request is automatically evaluated by our fraud detection pipeline. The system analyzes
            8 risk indicators in real-time: amount anomaly, transaction velocity, payment method history, geographic
            consistency, device fingerprint, trading behavior, recipient analysis, and card error patterns.
            Requests scoring above the threshold may be escalated for manual review.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { Alert, LinkedAccount, LockdownResult } from '~/utils/alertTypes'
import { INDICATOR_LABELS } from '~/utils/alertTypes'
import { formatCurrency, formatDate } from '~/utils/formatters'

defineProps<{
  visible: boolean
  alert: Alert | null
  linkedAccounts: LinkedAccount[]
  hasSharedCard: boolean
  allLinkedLocked: boolean
  lockdownResult: LockdownResult | null
  lockdownLoading: boolean
  cardCheckLoading: boolean
}>()

const emit = defineEmits<{
  close: []
  triggerLockdown: []
  viewCustomer: []
}>()

function riskColor(score: number): string {
  if (score >= 80) return 'text-red-600 bg-red-50'
  if (score >= 50) return 'text-amber-600 bg-amber-50'
  return 'text-green-600 bg-green-50'
}

function typeBadge(type: string): string {
  return type === 'block' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
}

function riskLevelBadge(level: string | undefined): string {
  if (!level) return 'bg-gray-100 text-gray-600'
  if (level === 'high' || level === 'critical') return 'bg-red-100 text-red-700'
  if (level === 'medium') return 'bg-amber-100 text-amber-700'
  return 'bg-green-100 text-green-700'
}

function decisionBadge(decision: string | undefined): string {
  if (decision === 'blocked') return 'bg-red-100 text-red-700'
  if (decision === 'escalated') return 'bg-amber-100 text-amber-700'
  return 'bg-green-100 text-green-700'
}
</script>

<template>
  <DialogRoot :open="visible && !!alert" @update:open="(v) => { if (!v) emit('close') }">
    <DialogPortal>
      <Transition
        enter-active-class="duration-200 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="duration-150 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <DialogOverlay v-if="visible && alert" force-mount class="fixed inset-0 z-[1100] bg-black/50" />
      </Transition>
      <Transition
        enter-active-class="duration-200 ease-out"
        enter-from-class="opacity-0 scale-95"
        enter-to-class="opacity-100 scale-100"
        leave-active-class="duration-150 ease-in"
        leave-from-class="opacity-100 scale-100"
        leave-to-class="opacity-0 scale-95"
      >
        <DialogContent v-if="visible && alert" force-mount class="fixed left-1/2 top-1/2 z-[1100] -translate-x-1/2 -translate-y-1/2 w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-xl">
          <DialogTitle class="sr-only">Alert Details</DialogTitle>
          <div class="flex items-center justify-between border-b border-gray-100 px-6 py-5">
            <h3 class="text-lg font-bold text-gray-900">Alert Details</h3>
            <button class="rounded-lg p-1.5 hover:bg-gray-100" @click="emit('close')">
              <Icon icon="lucide:x" class="h-5 w-5 text-gray-500" />
            </button>
          </div>

          <div class="max-h-[70vh] space-y-5 overflow-y-auto px-6 py-5">
            <!-- Customer Info -->
            <div class="rounded-lg bg-gray-50 p-4">
              <p class="text-sm font-semibold text-gray-800">{{ alert.customer_name }}</p>
              <p class="mt-0.5 text-xs text-gray-500">Account: {{ alert.account_id }}</p>
              <div class="mt-2.5 flex items-center gap-2">
                <span class="rounded px-1.5 py-0.5 text-xs font-bold uppercase" :class="typeBadge(alert.type)">{{ alert.type }}</span>
                <span class="rounded-full px-2 py-0.5 text-xs font-bold" :class="riskColor(alert.risk_score)">Risk: {{ alert.risk_score }}</span>
              </div>
            </div>

            <!-- Reason & Risk Breakdown -->
            <div v-if="alert.reason" class="rounded-lg border border-blue-200 bg-blue-50 p-4">
              <p class="text-xs font-semibold uppercase tracking-wider text-blue-700">Reason</p>
              <p class="mt-1.5 text-sm text-blue-900">{{ alert.reason }}</p>
              <div class="mt-2.5 flex items-center gap-2">
                <span v-if="alert.risk_level" class="rounded px-1.5 py-0.5 text-[10px] font-bold uppercase" :class="riskLevelBadge(alert.risk_level)">
                  {{ alert.risk_level }}
                </span>
                <span v-if="alert.decision" class="rounded px-1.5 py-0.5 text-[10px] font-bold uppercase" :class="decisionBadge(alert.decision)">
                  {{ alert.decision }}
                </span>
              </div>
            </div>

            <!-- Evaluation Summary (Gray Zone Reasoning) -->
            <div v-if="alert.evaluation_summary" class="rounded-lg border border-gray-200 bg-gray-50 p-4">
              <p class="text-xs font-semibold uppercase tracking-wider text-gray-500">Evaluation Summary</p>
              <p class="mt-1.5 text-sm leading-relaxed text-gray-700">{{ alert.evaluation_summary }}</p>
            </div>

            <!-- Lockdown Provenance -->
            <div v-if="alert.locked_by" class="flex items-center gap-2 rounded-lg border border-purple-200 bg-purple-50 px-4 py-3">
              <Icon icon="lucide:shield-check" class="h-4 w-4 text-purple-600" />
              <p class="text-xs text-purple-800">
                Locked by <span class="font-semibold">{{ alert.locked_by }}</span>
                <span v-if="alert.locked_at"> at {{ formatDate(alert.locked_at) }}</span>
              </p>
            </div>

            <!-- Connected Accounts -->
            <div v-if="linkedAccounts.length > 0" class="rounded-lg border border-orange-200 bg-orange-50 p-4">
              <p class="text-xs font-semibold uppercase tracking-wider text-orange-700">Connected Accounts</p>
              <ul class="mt-2 space-y-1.5">
                <li
                  v-for="account in linkedAccounts"
                  :key="account.customer_id"
                  class="flex items-center justify-between rounded px-2 py-1 text-xs"
                  :class="account.is_locked ? 'bg-gray-100 text-gray-500' : 'bg-white text-orange-900'"
                >
                  <span class="font-medium">{{ account.customer_name }}</span>
                  <span class="flex items-center gap-1.5">
                    <span v-if="account.is_locked" class="rounded bg-red-100 px-1.5 py-0.5 text-[10px] font-semibold text-red-700">
                      <Icon icon="lucide:lock" class="mr-0.5 inline h-2.5 w-2.5" />Locked
                    </span>
                    <span :class="account.is_locked ? 'text-gray-400' : 'text-orange-700'">{{ account.customer_id }}</span>
                  </span>
                </li>
              </ul>
            </div>

            <!-- Transaction -->
            <div>
              <p class="text-xs font-semibold uppercase tracking-wider text-gray-500">Triggered By</p>
              <p class="mt-1.5 text-sm text-gray-700">Withdrawal of <span class="font-bold">{{ formatCurrency(alert.amount, alert.currency) }}</span></p>
              <p class="mt-0.5 text-xs text-gray-400">{{ formatDate(alert.timestamp) }}</p>
            </div>

            <!-- Indicator Scores -->
            <div>
              <p class="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Indicator Scores</p>
              <div class="space-y-3">
                <div v-for="ind in alert.indicators" :key="ind.name">
                  <div class="flex items-center gap-2">
                    <span class="w-28 truncate text-xs text-gray-600">{{ INDICATOR_LABELS[ind.name] || ind.name }}</span>
                    <ProgressRoot
                      :model-value="ind.score"
                      :max="100"
                      class="h-1.5 flex-1 rounded-full bg-gray-100"
                    >
                      <ProgressIndicator
                        class="h-1.5 rounded-full transition-all"
                        :class="ind.score >= 80 ? 'bg-red-500' : ind.score >= 50 ? 'bg-amber-500' : 'bg-green-500'"
                        :style="{ width: `${ind.score}%` }"
                      />
                    </ProgressRoot>
                    <span class="w-8 text-right text-xs font-semibold" :class="ind.score >= 80 ? 'text-red-600' : ind.score >= 50 ? 'text-amber-600' : 'text-green-600'">{{ ind.score }}</span>
                  </div>
                  <p v-if="ind.reasoning" class="mt-1 pl-[7.5rem] text-[11px] leading-tight text-gray-500">{{ ind.reasoning }}</p>
                </div>
              </div>
            </div>

            <!-- Card Lockdown Result -->
            <div v-if="lockdownResult" class="rounded-lg border p-4" :class="lockdownResult.affected_count > 0 ? 'border-orange-200 bg-orange-50' : 'border-gray-200 bg-gray-50'">
              <p class="text-sm font-semibold" :class="lockdownResult.affected_count > 0 ? 'text-orange-800' : 'text-gray-700'">
                <Icon icon="lucide:shield-alert" class="mr-1 inline h-4 w-4" />
                {{ lockdownResult.affected_count > 0 ? 'Card Lockdown Executed' : 'No Linked Accounts Found' }}
              </p>
              <div v-if="lockdownResult.affected_count > 0" class="mt-1.5 text-xs text-orange-700">
                <p>{{ lockdownResult.affected_count }} account(s) locked:</p>
                <ul v-if="(lockdownResult.affected_accounts?.length ?? 0) > 0" class="mt-1.5 space-y-1">
                  <li
                    v-for="account in lockdownResult.affected_accounts"
                    :key="account.customer_id"
                    class="flex items-center justify-between rounded bg-white px-2 py-1 text-orange-900"
                  >
                    <span class="font-medium">{{ account.customer_name }}</span>
                    <span>{{ account.customer_id }}</span>
                  </li>
                </ul>
                <p v-else class="mt-1.5">{{ lockdownResult.affected_customers.join(', ') }}</p>
              </div>
              <p v-else class="mt-1.5 text-xs text-gray-500">No other accounts share a card with this customer.</p>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex gap-2 border-t border-gray-100 bg-gray-50/50 px-6 py-4">
            <button class="flex-1 rounded-lg bg-primary-600 py-2.5 text-sm font-medium text-white hover:bg-primary-700" @click="emit('viewCustomer')">View Customer</button>
            <button class="flex-1 rounded-lg border border-red-300 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50">Lock Account</button>
            <TooltipProvider>
              <TooltipRoot>
                <TooltipTrigger as-child>
                  <button
                    class="flex-1 rounded-lg border py-2.5 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"
                    :class="hasSharedCard && !allLinkedLocked ? 'border-orange-300 text-orange-600 hover:bg-orange-50' : 'border-gray-200 text-gray-400'"
                    :disabled="lockdownLoading || cardCheckLoading || !hasSharedCard || allLinkedLocked"
                    @click="emit('triggerLockdown')"
                  >
                    <Icon icon="lucide:credit-card" class="mr-1 inline h-3.5 w-3.5" />
                    {{ allLinkedLocked ? 'Cards Locked' : 'Card Lockdown' }}
                  </button>
                </TooltipTrigger>
                <TooltipPortal>
                  <TooltipContent
                    v-if="allLinkedLocked || !hasSharedCard"
                    side="top"
                    :side-offset="5"
                    class="z-[1200] rounded-lg bg-gray-900 px-3 py-1.5 text-xs text-white shadow-lg"
                  >
                    {{ allLinkedLocked ? 'All linked accounts already locked' : 'No shared card found for this customer' }}
                    <TooltipArrow class="fill-gray-900" />
                  </TooltipContent>
                </TooltipPortal>
              </TooltipRoot>
            </TooltipProvider>
            <button class="rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-500 hover:bg-gray-50" @click="emit('close')">Dismiss</button>
          </div>
        </DialogContent>
      </Transition>
    </DialogPortal>
  </DialogRoot>
</template>

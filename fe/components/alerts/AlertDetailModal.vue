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
}>()

function riskColor(score: number): string {
  if (score >= 80) return 'text-red-600 bg-red-50'
  if (score >= 50) return 'text-amber-600 bg-amber-50'
  return 'text-green-600 bg-green-50'
}

function typeBadge(type: string): string {
  return type === 'block' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition ease-out duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition ease-in duration-150"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="visible && alert" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" @click.self="emit('close')">
        <div class="w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-xl">
          <div class="flex items-center justify-between border-b border-gray-100 px-6 py-5">
            <h3 class="text-lg font-bold text-gray-900">Alert Details</h3>
            <button class="rounded-lg p-1.5 hover:bg-gray-100" @click="emit('close')">
              <Icon icon="lucide:x" class="h-5 w-5 text-gray-500" />
            </button>
          </div>

          <div class="space-y-5 px-6 py-5">
            <!-- Customer Info -->
            <div class="rounded-lg bg-gray-50 p-4">
              <p class="text-sm font-semibold text-gray-800">{{ alert.customer_name }}</p>
              <p class="mt-0.5 text-xs text-gray-500">Account: {{ alert.account_id }}</p>
              <div class="mt-2.5 flex items-center gap-2">
                <span class="rounded px-1.5 py-0.5 text-xs font-bold uppercase" :class="typeBadge(alert.type)">{{ alert.type }}</span>
                <span class="rounded-full px-2 py-0.5 text-xs font-bold" :class="riskColor(alert.risk_score)">Risk: {{ alert.risk_score }}</span>
              </div>
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
              <div class="space-y-2">
                <div v-for="ind in alert.indicators" :key="ind.name" class="flex items-center gap-2">
                  <span class="w-28 truncate text-xs text-gray-600">{{ INDICATOR_LABELS[ind.name] || ind.name }}</span>
                  <div class="h-1.5 flex-1 rounded-full bg-gray-100">
                    <div
                      class="h-1.5 rounded-full transition-all"
                      :class="ind.score >= 80 ? 'bg-red-500' : ind.score >= 50 ? 'bg-amber-500' : 'bg-green-500'"
                      :style="{ width: `${ind.score}%` }"
                    />
                  </div>
                  <span class="w-8 text-right text-xs font-semibold" :class="ind.score >= 80 ? 'text-red-600' : ind.score >= 50 ? 'text-amber-600' : 'text-green-600'">{{ ind.score }}</span>
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
            <button class="flex-1 rounded-lg bg-primary-600 py-2.5 text-sm font-medium text-white hover:bg-primary-700">View Customer</button>
            <button class="flex-1 rounded-lg border border-red-300 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50">Lock Account</button>
            <button
              class="flex-1 rounded-lg border py-2.5 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"
              :class="hasSharedCard && !allLinkedLocked ? 'border-orange-300 text-orange-600 hover:bg-orange-50' : 'border-gray-200 text-gray-400'"
              :disabled="lockdownLoading || cardCheckLoading || !hasSharedCard || allLinkedLocked"
              :title="allLinkedLocked ? 'All linked accounts already locked' : !hasSharedCard ? 'No shared card found for this customer' : ''"
              @click="emit('triggerLockdown')"
            >
              <Icon icon="lucide:credit-card" class="mr-1 inline h-3.5 w-3.5" />
              {{ allLinkedLocked ? 'Cards Locked' : 'Card Lockdown' }}
            </button>
            <button class="rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-500 hover:bg-gray-50" @click="emit('close')">Dismiss</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { PATTERN_ICONS } from '~/utils/alertTypes'

useHead({ title: 'Nexa' })

const {
  alerts,
  fraudPatterns,
  admins,
  currentAdmin,
  timeRange,
  customSince,
  customUntil,
  selectedIds,
  selectedAlert,
  showDetail,
  bulkLoading,
  lockdownLoading,
  lockdownResult,
  cardCheckCache,
  cardCheckLoading,
  escalationCount,
  blockCount,
  unreadCount,
  riskColor,
  typeBadge,
  relativeTime,
  toggleSelect,
  toggleAll,
  openDetail,
  bulkAction,
  triggerCardLockdown,
  hasSharedCard,
  linkedAccounts,
  allLinkedLocked,
} = useAlerts()

const showCustomerDrawer = ref(false)
const selectedCustomerId = ref('')

function handleViewCustomer() {
  if (selectedAlert.value) {
    selectedCustomerId.value = selectedAlert.value.account_id
    showCustomerDrawer.value = true
  }
}
</script>

<template>
  <div>
    <!-- Header -->
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Alerts & Fraud Detection</h1>
        <p class="mt-1 text-sm text-gray-500">Real-time fraud detection and incident response</p>
      </div>
      <div class="flex items-center gap-3">
        <SelectRoot
          v-if="admins.length > 0"
          :model-value="currentAdmin?.id ?? ''"
          @update:model-value="(val: string) => { currentAdmin = admins.find(a => a.id === val) ?? null }"
        >
          <SelectTrigger class="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500">
            <SelectValue placeholder="Acting as..." />
            <SelectIcon>
              <Icon icon="lucide:chevron-down" class="h-4 w-4 text-gray-400" />
            </SelectIcon>
          </SelectTrigger>
          <SelectPortal>
            <SelectContent class="z-[1200] max-h-60 overflow-auto rounded-lg bg-white border border-gray-200 shadow-lg" position="popper" :side-offset="4">
              <SelectViewport>
                <SelectItem
                  v-for="admin in admins"
                  :key="admin.id"
                  :value="admin.id"
                  class="relative cursor-pointer select-none px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 data-[highlighted]:bg-gray-50 outline-none"
                >
                  <SelectItemText>{{ admin.name }}</SelectItemText>
                  <SelectItemIndicator class="absolute right-2 top-1/2 -translate-y-1/2">
                    <Icon icon="lucide:check" class="h-4 w-4 text-primary-600" />
                  </SelectItemIndicator>
                </SelectItem>
              </SelectViewport>
            </SelectContent>
          </SelectPortal>
        </SelectRoot>
        <CommonNotificationDropdown />
      </div>
    </div>

    <AlertsSummaryBar :escalation-count="escalationCount" :block-count="blockCount" :unread-count="unreadCount" />

    <div class="my-4">
      <AlertsTimeRangeFilter v-model="timeRange" v-model:since="customSince" v-model:until="customUntil" />
    </div>

    <AlertsBulkActions :selected-count="selectedIds.size" :loading="bulkLoading" @action="bulkAction" />

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-3">
      <div class="xl:col-span-2">
        <AlertsAlertList
          :alerts="alerts"
          :risk-color="riskColor"
          :type-badge="typeBadge"
          :relative-time="relativeTime"
        />
      </div>

      <AlertsFraudPatternCards :patterns="fraudPatterns" :pattern-icons="PATTERN_ICONS" />
    </div>

    <AlertsAlertDetailModal
      :visible="showDetail"
      :alert="selectedAlert"
      :linked-accounts="selectedAlert ? linkedAccounts(selectedAlert) : []"
      :has-shared-card="selectedAlert ? hasSharedCard(selectedAlert) : false"
      :all-linked-locked="selectedAlert ? allLinkedLocked(selectedAlert) : false"
      :lockdown-result="lockdownResult"
      :lockdown-loading="lockdownLoading"
      :card-check-loading="cardCheckLoading"
      @close="showDetail = false"
      @trigger-lockdown="triggerCardLockdown"
      @view-customer="handleViewCustomer"
    />

    <ScoringFactorsDrawer
      :visible="showCustomerDrawer"
      :customer-id="selectedCustomerId"
      :customer-name="selectedAlert?.customer_name"
      :risk-score="0"
      decision=""
      @close="showCustomerDrawer = false; selectedCustomerId = ''"
    />
  </div>
</template>

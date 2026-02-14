<script setup lang="ts">
import { PATTERN_ICONS } from '~/utils/alertTypes'

useHead({ title: 'Alerts - Nexa' })

const {
  alerts,
  fraudPatterns,
  admins,
  currentAdmin,
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

function selectAdmin(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  currentAdmin.value = admins.value.find(a => a.id === value) ?? null
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
        <select
          v-if="admins.length > 0"
          class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          :value="currentAdmin?.id ?? ''"
          @change="selectAdmin"
        >
          <option value="" disabled>Acting as...</option>
          <option v-for="admin in admins" :key="admin.id" :value="admin.id">{{ admin.name }}</option>
        </select>
        <CommonNotificationDropdown />
      </div>
    </div>

    <AlertsSummaryBar :escalation-count="escalationCount" :block-count="blockCount" :unread-count="unreadCount" />

    <AlertsBulkActions :selected-count="selectedIds.size" :loading="bulkLoading" @action="bulkAction" />

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-3">
      <div class="xl:col-span-2">
        <AlertsAlertList
          :alerts="alerts"
          :selected-ids="selectedIds"
          :card-check-cache="cardCheckCache"
          :risk-color="riskColor"
          :type-badge="typeBadge"
          :relative-time="relativeTime"
          @select="toggleSelect"
          @select-all="toggleAll"
          @open-detail="openDetail"
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
    />
  </div>
</template>

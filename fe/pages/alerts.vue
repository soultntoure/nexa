<script setup lang="ts">
import { PATTERN_ICONS } from '~/utils/alertTypes'

useHead({ title: 'Alerts - Nexa' })

const {
  alerts,
  fraudPatterns,
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
</script>

<template>
  <div>
    <!-- Header -->
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Alerts & Fraud Detection</h1>
        <p class="mt-1 text-sm text-gray-500">Real-time fraud detection and incident response</p>
      </div>
      <CommonNotificationDropdown />
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

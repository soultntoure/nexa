<script setup lang="ts">
import { Icon } from '@iconify/vue'

defineProps<{
  escalationCount: number
  blockCount: number
  unreadCount: number
}>()
</script>

<template>
  <div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
    <div class="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
      <Icon icon="lucide:alert-triangle" class="h-6 w-6 text-amber-600" />
      <div>
        <p class="text-2xl font-bold text-amber-700">{{ escalationCount }}</p>
        <p class="text-xs text-amber-600">Escalation Alerts</p>
      </div>
    </div>
    <div class="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-4">
      <Icon icon="lucide:shield-off" class="h-6 w-6 text-red-600" />
      <div>
        <p class="text-2xl font-bold text-red-700">{{ blockCount }}</p>
        <p class="text-xs text-red-600">Block Alerts</p>
      </div>
    </div>
    <div class="flex items-center gap-3 rounded-xl border border-blue-200 bg-blue-50 p-4">
      <Icon icon="lucide:mail" class="h-6 w-6 text-blue-600" />
      <div>
        <p class="text-2xl font-bold text-blue-700">{{ unreadCount }}</p>
        <p class="text-xs text-blue-600">Unread Alerts</p>
      </div>
    </div>
  </div>
</template>

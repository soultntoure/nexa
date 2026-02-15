<script setup lang="ts">
import { Icon } from '@iconify/vue'

defineProps<{
  selectedCount: number
  isSubmitting: boolean
}>()

const emit = defineEmits<{
  'batch-approve': [reason: string]
  'batch-block': [reason: string]
  clear: []
}>()

const reason = ref('')
const pendingAction = ref<'approved' | 'blocked' | null>(null)

function startAction(action: 'approved' | 'blocked') {
  pendingAction.value = action
  reason.value = ''
}

function confirmAction() {
  if (!reason.value.trim() || !pendingAction.value) return
  if (pendingAction.value === 'approved') {
    emit('batch-approve', reason.value.trim())
  } else {
    emit('batch-block', reason.value.trim())
  }
  pendingAction.value = null
  reason.value = ''
}

function cancel() {
  pendingAction.value = null
  reason.value = ''
}
</script>

<template>
  <div class="shrink-0 flex items-center gap-2 px-3 py-2 border-b border-gray-200 bg-gray-50 text-xs">
    <span class="text-gray-500">{{ selectedCount }} selected</span>

    <template v-if="!pendingAction">
      <button
        class="px-2 py-1 text-gray-600 border border-gray-200 rounded hover:bg-white transition-colors disabled:opacity-40"
        :disabled="isSubmitting"
        @click="startAction('approved')"
      >
        Approve
      </button>
      <button
        class="px-2 py-1 text-gray-600 border border-gray-200 rounded hover:bg-white transition-colors disabled:opacity-40"
        :disabled="isSubmitting"
        @click="startAction('blocked')"
      >
        Block
      </button>
      <button
        class="ml-auto px-2 py-1 text-gray-400 hover:text-gray-600 transition-colors"
        @click="emit('clear')"
      >
        <Icon icon="lucide:x" class="w-3.5 h-3.5" />
      </button>
    </template>

    <template v-else>
      <input
        v-model="reason"
        type="text"
        class="flex-1 px-2 py-1 text-xs border border-gray-200 rounded focus:ring-1 focus:ring-gray-300 focus:border-gray-300 outline-none"
        :placeholder="`Reason to ${pendingAction}...`"
        @keyup.enter="confirmAction"
      >
      <button
        class="px-2 py-1 text-gray-700 border border-gray-200 rounded hover:bg-white transition-colors disabled:opacity-40"
        :disabled="!reason.trim() || isSubmitting"
        @click="confirmAction"
      >
        <Icon v-if="isSubmitting" icon="lucide:loader-2" class="w-3 h-3 animate-spin" />
        <span v-else>Confirm</span>
      </button>
      <button
        class="px-2 py-1 text-gray-400 hover:text-gray-600 transition-colors"
        @click="cancel"
      >
        <Icon icon="lucide:x" class="w-3.5 h-3.5" />
      </button>
    </template>
  </div>
</template>

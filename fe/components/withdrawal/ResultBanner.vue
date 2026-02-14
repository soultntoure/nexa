<script setup lang="ts">
import { Icon } from '@iconify/vue'

defineProps<{
  showFraudNotice: boolean
  showSuccess: boolean
  evalResult: { decision: 'approved' | 'escalated' | 'blocked' } | null
}>()

const emit = defineEmits<{
  dismiss: []
}>()
</script>

<template>
  <!-- Processing Spinner -->
  <Transition
    enter-active-class="transition ease-out duration-200"
    enter-from-class="opacity-0 -translate-y-2"
    enter-to-class="opacity-100 translate-y-0"
    leave-active-class="transition ease-in duration-150"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div v-if="showFraudNotice" class="flex flex-col items-center justify-center py-10">
      <Icon icon="lucide:loader-2" class="w-8 h-8 text-primary-600 animate-spin" />
      <p class="text-sm font-medium text-gray-600 mt-3">Processing your withdrawal...</p>
    </div>
  </Transition>

  <!-- Success Fallback -->
  <Transition
    enter-active-class="transition ease-out duration-200"
    enter-from-class="opacity-0 -translate-y-2"
    enter-to-class="opacity-100 translate-y-0"
    leave-active-class="transition ease-in duration-150"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div v-if="showSuccess" class="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-3">
      <Icon icon="lucide:check-circle" class="w-5 h-5 text-green-600 shrink-0" />
      <div>
        <p class="text-sm font-medium text-green-800">Withdrawal request submitted!</p>
        <p class="text-xs text-green-600 mt-0.5">Your request has been approved and is being processed. Track it on the Transactions page.</p>
      </div>
    </div>
  </Transition>

  <!-- Eval Result -->
  <Transition
    enter-active-class="transition ease-out duration-300"
    enter-from-class="opacity-0 -translate-y-2"
    enter-to-class="opacity-100 translate-y-0"
    leave-active-class="transition ease-in duration-150"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <!-- Approved -->
    <div v-if="evalResult?.decision === 'approved'" class="rounded-xl border border-green-200 bg-green-50/50 p-5">
      <div class="flex items-center gap-3 mb-3">
        <Icon icon="lucide:check-circle" class="w-6 h-6 text-green-600" />
        <span class="text-lg font-semibold text-green-800">Withdrawal Approved</span>
      </div>
      <p class="text-sm text-green-700 leading-relaxed">Your withdrawal has been approved and is being processed. You can track its status on the Transactions page.</p>
      <div class="mt-4 flex justify-end">
        <button
          class="px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          @click="emit('dismiss')"
        >
          New Withdrawal
        </button>
      </div>
    </div>

    <!-- Under Review -->
    <div v-else-if="evalResult" class="rounded-xl border border-yellow-200 bg-yellow-50/50 p-5">
      <div class="flex items-center gap-3 mb-3">
        <Icon icon="lucide:clock" class="w-6 h-6 text-yellow-600" />
        <span class="text-lg font-semibold text-yellow-800">Withdrawal Under Review</span>
      </div>
      <p class="text-sm text-yellow-700 leading-relaxed">Your withdrawal is under review. You will be notified once it has been processed. This usually takes 1-2 business days.</p>
      <div class="mt-4 flex justify-end">
        <button
          class="px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          @click="emit('dismiss')"
        >
          New Withdrawal
        </button>
      </div>
    </div>
  </Transition>
</template>

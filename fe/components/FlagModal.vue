<script setup lang="ts">
import { Icon } from '@iconify/vue'

const props = defineProps<{
  visible: boolean
  transactionId: string
  customerName: string
}>()

const emit = defineEmits<{
  close: []
  submit: [data: { reason: string; notes: string }]
}>()

const selectedReason = ref('')
const customNotes = ref('')

const flagReasons = [
  { value: 'suspicious_activity', label: 'Suspicious Activity Pattern' },
  { value: 'identity_mismatch', label: 'Identity Mismatch' },
  { value: 'unusual_amount', label: 'Unusual Transaction Amount' },
  { value: 'geographic_anomaly', label: 'Geographic Anomaly' },
  { value: 'device_concern', label: 'Device / Browser Concern' },
  { value: 'multiple_accounts', label: 'Suspected Multiple Accounts' },
  { value: 'regulatory', label: 'Regulatory / Compliance Concern' },
  { value: 'other', label: 'Other (specify below)' },
]

const canSubmit = computed(() => {
  if (!selectedReason.value) return false
  if (selectedReason.value === 'other' && !customNotes.value.trim()) return false
  return true
})

function handleSubmit() {
  if (!canSubmit.value) return
  emit('submit', {
    reason: selectedReason.value,
    notes: customNotes.value,
  })
  selectedReason.value = ''
  customNotes.value = ''
}

function handleClose() {
  selectedReason.value = ''
  customNotes.value = ''
  emit('close')
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
      <div
        v-if="visible"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div class="absolute inset-0 bg-black/50" @click="handleClose" />

        <div class="relative bg-white rounded-xl shadow-2xl w-full max-w-md">
          <!-- Header -->
          <div class="flex items-center justify-between p-5 border-b border-gray-200">
            <div class="flex items-center gap-2">
              <div class="p-2 bg-orange-100 rounded-lg">
                <Icon icon="lucide:flag" class="w-5 h-5 text-orange-600" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-gray-900">Flag Account</h3>
                <p class="text-sm text-gray-500">{{ customerName }} - {{ transactionId }}</p>
              </div>
            </div>
            <button class="p-1.5 hover:bg-gray-100 rounded-lg transition-colors" @click="handleClose">
              <Icon icon="lucide:x" class="w-5 h-5 text-gray-400" />
            </button>
          </div>

          <!-- Body -->
          <div class="p-5 space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Reason for Flagging</label>
              <div class="space-y-2">
                <label
                  v-for="reason in flagReasons"
                  :key="reason.value"
                  class="flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all"
                  :class="selectedReason === reason.value
                    ? 'border-orange-300 bg-orange-50'
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'"
                >
                  <input
                    v-model="selectedReason"
                    type="radio"
                    :value="reason.value"
                    class="text-orange-500 focus:ring-orange-500"
                  >
                  <span class="text-sm text-gray-700">{{ reason.label }}</span>
                </label>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1.5">
                Additional Notes
                <span v-if="selectedReason === 'other'" class="text-red-500">*</span>
              </label>
              <textarea
                v-model="customNotes"
                rows="3"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-500 focus:border-orange-500 resize-none"
                placeholder="Provide additional context for the flag..."
              />
            </div>
          </div>

          <!-- Footer -->
          <div class="flex items-center justify-end gap-3 p-5 border-t border-gray-200">
            <button
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              @click="handleClose"
            >
              Cancel
            </button>
            <button
              class="px-4 py-2 text-sm font-medium text-white bg-orange-500 rounded-lg hover:bg-orange-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="!canSubmit"
              @click="handleSubmit"
            >
              Flag Account
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

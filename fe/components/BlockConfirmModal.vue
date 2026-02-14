<script setup lang="ts">
import { Icon } from '@iconify/vue'

interface LinkedAccount {
  customer_id: string
  customer_name: string
  is_locked?: boolean
}

const props = defineProps<{
  visible: boolean
  customerName: string
  accountId: string
}>()

const emit = defineEmits<{
  close: []
  confirm: [justification: string, lockConnected: boolean]
}>()

const loading = ref(false)
const linkedAccounts = ref<LinkedAccount[]>([])
const lockConnected = ref(true)
const justification = ref('')

watch(() => props.visible, async (open) => {
  if (!open) return
  justification.value = ''
  lockConnected.value = true
  if (!props.accountId) return
  loading.value = true
  linkedAccounts.value = []
  try {
    const result = await $fetch<{ shared: boolean; linked_count: number; linked_accounts?: LinkedAccount[] }>(
      `/api/alerts/card-check/${props.accountId}`,
    )
    linkedAccounts.value = (result.linked_accounts ?? []).filter(a => a.customer_id !== props.accountId)
  } catch {
    linkedAccounts.value = []
  } finally {
    loading.value = false
  }
})

const hasConnected = computed(() => linkedAccounts.value.length > 0)
const canSubmit = computed(() => justification.value.trim().length > 0 && !loading.value)

function handleConfirm() {
  if (!canSubmit.value) return
  emit('confirm', justification.value.trim(), hasConnected.value && lockConnected.value)
}
</script>

<template>
  <DialogRoot :open="visible" @update:open="(v) => { if (!v) emit('close') }">
    <DialogPortal>
      <Transition
        enter-active-class="duration-200 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="duration-150 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <DialogOverlay v-if="visible" force-mount class="fixed inset-0 z-[1100] bg-black/50" />
      </Transition>
      <Transition
        enter-active-class="duration-200 ease-out"
        enter-from-class="opacity-0 scale-95"
        enter-to-class="opacity-100 scale-100"
        leave-active-class="duration-150 ease-in"
        leave-from-class="opacity-100 scale-100"
        leave-to-class="opacity-0 scale-95"
      >
        <DialogContent v-if="visible" force-mount class="fixed left-1/2 top-1/2 z-[1100] -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-2xl w-full max-w-md">
          <DialogTitle class="sr-only">Block Customer Confirmation</DialogTitle>
          <!-- Header -->
          <div class="flex items-center justify-between p-5 border-b border-gray-200">
            <div class="flex items-center gap-2">
              <div class="p-2 bg-red-100 rounded-lg">
                <Icon icon="lucide:ban" class="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-gray-900">Block Withdrawal</h3>
                <p class="text-sm text-gray-500">{{ customerName }}</p>
              </div>
            </div>
            <button class="p-1.5 hover:bg-gray-100 rounded-lg transition-colors" @click="emit('close')">
              <Icon icon="lucide:x" class="w-5 h-5 text-gray-400" />
            </button>
          </div>

          <!-- Body -->
          <div class="p-5 space-y-4">
            <!-- Justification -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1.5">
                Reason for blocking <span class="text-red-500">*</span>
              </label>
              <textarea
                v-model="justification"
                rows="3"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-red-500 focus:border-red-500 resize-none"
                placeholder="Provide your reasoning for blocking this withdrawal..."
              />
            </div>

            <!-- Loading state -->
            <div v-if="loading" class="flex items-center justify-center py-4">
              <Icon icon="lucide:loader-2" class="w-5 h-5 text-gray-400 animate-spin" />
              <span class="ml-2 text-sm text-gray-500">Checking connected accounts...</span>
            </div>

            <!-- Connected accounts found -->
            <div v-else-if="hasConnected" class="space-y-3">
              <div class="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
                <Icon icon="lucide:alert-triangle" class="w-5 h-5 text-amber-600 shrink-0" />
                <p class="text-sm text-amber-800">
                  <strong>{{ linkedAccounts.length }}</strong> connected account{{ linkedAccounts.length > 1 ? 's' : '' }} detected sharing payment methods.
                </p>
              </div>

              <div class="rounded-lg border border-gray-200 divide-y divide-gray-100">
                <div
                  v-for="account in linkedAccounts"
                  :key="account.customer_id"
                  class="flex items-center justify-between px-3 py-2.5"
                >
                  <div class="flex items-center gap-2">
                    <Icon icon="lucide:user" class="w-4 h-4 text-gray-400" />
                    <div>
                      <p class="text-sm font-medium text-gray-800">{{ account.customer_name }}</p>
                      <p class="text-xs text-gray-500 font-mono">{{ account.customer_id }}</p>
                    </div>
                  </div>
                  <span
                    v-if="account.is_locked"
                    class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700"
                  >
                    <Icon icon="lucide:lock" class="w-3 h-3" />
                    Locked
                  </span>
                </div>
              </div>

              <label class="flex items-start gap-3 cursor-pointer rounded-lg border border-gray-200 p-3 hover:bg-gray-50 transition-colors">
                <input
                  v-model="lockConnected"
                  type="checkbox"
                  class="mt-0.5 rounded text-red-600 focus:ring-red-500"
                />
                <div>
                  <p class="text-sm font-medium text-gray-800">Lock all connected accounts</p>
                  <p class="text-xs text-gray-500">Block withdrawals on all {{ linkedAccounts.length }} linked account{{ linkedAccounts.length > 1 ? 's' : '' }} sharing the same payment method.</p>
                </div>
              </label>
            </div>

            <!-- No connected accounts -->
            <div v-else class="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 p-3">
              <Icon icon="lucide:check-circle" class="w-5 h-5 text-green-500 shrink-0" />
              <p class="text-sm text-gray-600">No connected accounts found. Only this withdrawal will be blocked.</p>
            </div>
          </div>

          <!-- Footer -->
          <div class="flex items-center justify-end gap-3 p-5 border-t border-gray-200">
            <button
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              @click="emit('close')"
            >
              Cancel
            </button>
            <button
              class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              :disabled="!canSubmit"
              @click="handleConfirm"
            >
              <Icon icon="lucide:ban" class="w-4 h-4" />
              {{ hasConnected && lockConnected ? `Block + Lock ${linkedAccounts.length} Account${linkedAccounts.length > 1 ? 's' : ''}` : 'Block Withdrawal' }}
            </button>
          </div>
        </DialogContent>
      </Transition>
    </DialogPortal>
  </DialogRoot>
</template>

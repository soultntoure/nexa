<script setup lang="ts">
import { Icon } from '@iconify/vue'

useHead({ title: 'Settings - Nexa' })

const tabs = [
  { key: 'fraud', label: 'Fraud Detection', icon: 'lucide:shield' },
  { key: 'audit', label: 'Background Audit', icon: 'lucide:scan-search' },
] as const

type TabKey = typeof tabs[number]['key']

const activeTab = ref<TabKey>('fraud')
const showSaved = ref(false)

interface TabChild {
  save: () => Promise<void>
  resetDefaults: () => void
  isSaving: { value: boolean }
}

const fraudRef = ref<TabChild | null>(null)
const auditRef = ref<TabChild | null>(null)

const activeChild = computed(() =>
  activeTab.value === 'fraud' ? fraudRef.value : auditRef.value,
)

const isSaving = computed(() => activeChild.value?.isSaving.value ?? false)

function handleSaved(): void {
  showSaved.value = true
  setTimeout(() => { showSaved.value = false }, 2000)
}

async function save(): Promise<void> {
  await activeChild.value?.save()
}

function resetDefaults(): void {
  activeChild.value?.resetDefaults()
}
</script>

<template>
  <div class="max-w-4xl space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Settings</h1>
        <p class="mt-1 text-sm text-gray-500">Configure fraud detection thresholds and system preferences</p>
      </div>
      <div class="flex items-center gap-2">
        <Transition
          enter-active-class="transition ease-out duration-200"
          enter-from-class="opacity-0"
          enter-to-class="opacity-100"
          leave-active-class="transition ease-in duration-150"
          leave-from-class="opacity-100"
          leave-to-class="opacity-0"
        >
          <span v-if="showSaved" class="flex items-center gap-1 text-sm text-green-600">
            <Icon icon="lucide:check" class="h-4 w-4" />
            Saved
          </span>
        </Transition>
        <button
          class="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          @click="resetDefaults"
        >
          Reset Defaults
        </button>
        <button
          class="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          :disabled="isSaving"
          @click="save"
        >
          <Icon v-if="isSaving" icon="lucide:loader-2" class="h-4 w-4 animate-spin" />
          {{ isSaving ? 'Saving...' : 'Save Changes' }}
        </button>
      </div>
    </div>

    <!-- Tab Navigation -->
    <div class="border-b border-gray-200">
      <nav class="-mb-px flex gap-6">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="flex items-center gap-2 border-b-2 px-1 pb-3 text-sm font-medium transition-colors"
          :class="activeTab === tab.key
            ? 'border-primary-600 text-primary-600'
            : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'"
          @click="activeTab = tab.key"
        >
          <Icon :icon="tab.icon" class="h-4 w-4" />
          {{ tab.label }}
        </button>
      </nav>
    </div>

    <!-- Tab Content -->
    <SettingsFraudDetection v-if="activeTab === 'fraud'" ref="fraudRef" @saved="handleSaved" />
    <SettingsAuditConfig v-if="activeTab === 'audit'" ref="auditRef" @saved="handleSaved" />
  </div>
</template>

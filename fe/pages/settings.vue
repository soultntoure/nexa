<script setup lang="ts">
import { Icon } from '@iconify/vue'

useHead({ title: 'Nexa' })

const tabs = [
  { key: 'fraud', label: 'Fraud Detection', icon: 'lucide:shield' },
  { key: 'audit', label: 'Background Audit', icon: 'lucide:scan-search' },
] as const

type TabKey = typeof tabs[number]['key']

const activeTab = ref<TabKey>('fraud')

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

function handleSaved(): void {}

async function save(): Promise<void> {
  await activeChild.value?.save()
}

function resetDefaults(): void {
  activeChild.value?.resetDefaults()
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Settings</h1>
        <p class="mt-1 text-sm text-gray-500">Configure fraud detection thresholds and system preferences</p>
      </div>
      <div class="flex items-center gap-2">
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
    <TabsRoot v-model="activeTab">
      <TabsList class="border-b border-gray-200">
        <nav class="-mb-px flex">
          <TabsTrigger
            v-for="tab in tabs"
            :key="tab.key"
            :value="tab.key"
            class="flex items-center gap-2 border-b-2 border-transparent px-1 pb-3 text-sm font-medium transition-colors text-gray-500 hover:border-gray-300 hover:text-gray-700 data-[state=active]:border-primary-600 data-[state=active]:text-primary-600"
          >
            {{ tab.label }}
          </TabsTrigger>
        </nav>
      </TabsList>
    </TabsRoot>

    <!-- Tab Content -->
    <SettingsFraudDetection v-if="activeTab === 'fraud'" ref="fraudRef" @saved="handleSaved" />
    <SettingsAuditConfig v-if="activeTab === 'audit'" ref="auditRef" @saved="handleSaved" />
  </div>
</template>

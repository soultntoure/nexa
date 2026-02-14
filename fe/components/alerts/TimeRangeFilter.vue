<script setup lang="ts">
import { Icon } from '@iconify/vue'

const model = defineModel<string>({ default: '' })
const since = defineModel<string>('since', { default: '' })
const until = defineModel<string>('until', { default: '' })

const presets = [
  { label: 'All', value: '' },
  { label: '1h', value: String(60 * 60 * 1000) },
  { label: '6h', value: String(6 * 60 * 60 * 1000) },
  { label: '24h', value: String(24 * 60 * 60 * 1000) },
  { label: '7d', value: String(7 * 24 * 60 * 60 * 1000) },
  { label: '30d', value: String(30 * 24 * 60 * 60 * 1000) },
]

function handleTabChange(value: string | number) {
  model.value = String(value)
  if (value !== 'custom') {
    since.value = ''
    until.value = ''
  }
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-2">
    <TabsRoot :model-value="model" @update:model-value="handleTabChange">
      <TabsList class="flex items-center gap-1 rounded-lg bg-gray-100 p-1">
        <TabsTrigger
          v-for="opt in presets"
          :key="opt.value"
          :value="opt.value"
          class="rounded-md px-3 py-1.5 text-xs font-medium transition-colors text-gray-500 hover:text-gray-700 data-[state=active]:bg-white data-[state=active]:text-gray-900 data-[state=active]:shadow-sm"
        >
          {{ opt.label }}
        </TabsTrigger>
        <TabsTrigger
          value="custom"
          class="rounded-md px-3 py-1.5 text-xs font-medium transition-colors text-gray-500 hover:text-gray-700 data-[state=active]:bg-white data-[state=active]:text-gray-900 data-[state=active]:shadow-sm"
        >
          <Icon icon="lucide:calendar-range" class="mr-1 inline h-3 w-3" />
          Custom
        </TabsTrigger>
      </TabsList>
    </TabsRoot>

    <div v-if="model === 'custom'" class="flex items-center gap-2">
      <input
        v-model="since"
        type="datetime-local"
        class="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs text-gray-700 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
      />
      <span class="text-xs text-gray-400">to</span>
      <input
        v-model="until"
        type="datetime-local"
        class="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs text-gray-700 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
      />
    </div>
  </div>
</template>

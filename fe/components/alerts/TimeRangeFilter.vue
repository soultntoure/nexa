<script setup lang="ts">
const model = defineModel<string>({ default: '' })

const options = [
  { label: 'All', value: '' },
  { label: '1h', value: String(60 * 60 * 1000) },
  { label: '6h', value: String(6 * 60 * 60 * 1000) },
  { label: '24h', value: String(24 * 60 * 60 * 1000) },
  { label: '7d', value: String(7 * 24 * 60 * 60 * 1000) },
  { label: '30d', value: String(30 * 24 * 60 * 60 * 1000) },
]
</script>

<template>
  <div class="flex items-center gap-1 rounded-lg bg-gray-100 p-1">
    <button
      v-for="opt in options"
      :key="opt.value"
      class="px-3 py-1.5 text-xs font-medium rounded-md transition-colors"
      :class="model === opt.value
        ? 'bg-white text-gray-900 shadow-sm'
        : 'text-gray-500 hover:text-gray-700'"
      @click="model = opt.value"
    >
      {{ opt.label }}
    </button>
  </div>
</template>

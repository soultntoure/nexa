<script setup lang="ts">
import { Icon } from '@iconify/vue'

const model = defineModel<string>({ required: true })
defineProps<{ disabled: boolean }>()
const emit = defineEmits<{ submit: [] }>()
const inputEl = ref<HTMLInputElement>()

function focus() {
  inputEl.value?.focus()
}

defineExpose({ focus })
</script>

<template>
  <div class="border-t border-gray-200 p-4">
    <form class="flex items-center gap-3" @submit.prevent="emit('submit')">
      <input
        ref="inputEl"
        v-model="model"
        type="text"
        placeholder="Ask about fraud patterns, account behavior, or transactions..."
        class="flex-1 rounded-xl border border-gray-300 px-4 py-3 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500"
        :disabled="disabled"
      />
      <button
        type="submit"
        class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary-600 text-white transition-colors hover:bg-primary-700 disabled:opacity-50"
        :disabled="!model.trim() || disabled"
      >
        <Icon icon="lucide:send" class="h-5 w-5" />
      </button>
    </form>
  </div>
</template>

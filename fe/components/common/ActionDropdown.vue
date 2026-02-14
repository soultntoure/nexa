<script setup lang="ts">
import { Icon } from '@iconify/vue'

interface Action {
  label: string
  icon: string
  color?: string
  handler: () => void
}

defineProps<{
  actions: Action[]
}>()

const isOpen = ref(false)
const dropdownRef = ref<HTMLElement>()

const colorClasses: Record<string, string> = {
  green: 'text-green-600 hover:bg-green-50',
  orange: 'text-orange-600 hover:bg-orange-50',
  red: 'text-red-600 hover:bg-red-50',
}

function getActionClass(color?: string): string {
  if (color && colorClasses[color]) return colorClasses[color]
  return 'text-gray-700 hover:bg-gray-50'
}

function toggle() {
  isOpen.value = !isOpen.value
}

function handleAction(action: Action) {
  isOpen.value = false
  action.handler()
}

function handleClickOutside(e: MouseEvent) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => document.addEventListener('click', handleClickOutside))
onUnmounted(() => document.removeEventListener('click', handleClickOutside))
</script>

<template>
  <div ref="dropdownRef" class="relative">
    <button
      class="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
      @click.stop="toggle"
    >
      <Icon icon="lucide:more-vertical" class="w-4 h-4 text-gray-500" />
    </button>

    <Transition
      enter-active-class="transition ease-out duration-100"
      enter-from-class="transform opacity-0 scale-95"
      enter-to-class="transform opacity-100 scale-100"
      leave-active-class="transition ease-in duration-75"
      leave-from-class="transform opacity-100 scale-100"
      leave-to-class="transform opacity-0 scale-95"
    >
      <div
        v-if="isOpen"
        class="absolute right-0 z-50 mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1"
      >
        <button
          v-for="action in actions"
          :key="action.label"
          class="w-full flex items-center gap-2.5 px-3 py-2 text-sm transition-colors"
          :class="getActionClass(action.color)"
          @click="handleAction(action)"
        >
          <Icon :icon="action.icon" class="w-4 h-4 shrink-0" />
          <span>{{ action.label }}</span>
        </button>
      </div>
    </Transition>
  </div>
</template>

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

const colorClasses: Record<string, string> = {
  green: 'text-green-600 hover:bg-green-50',
  orange: 'text-orange-600 hover:bg-orange-50',
  red: 'text-red-600 hover:bg-red-50',
}

function getActionClass(color?: string): string {
  if (color && colorClasses[color]) return colorClasses[color]
  return 'text-gray-700 hover:bg-gray-50'
}
</script>

<template>
  <DropdownMenuRoot>
    <DropdownMenuTrigger as-child>
      <button
        class="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
      >
        <Icon icon="lucide:more-vertical" class="w-4 h-4 text-gray-500" />
      </button>
    </DropdownMenuTrigger>
    <DropdownMenuPortal>
      <DropdownMenuContent
        class="z-[1200] w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1"
        :side-offset="4"
        align="end"
      >
        <DropdownMenuItem
          v-for="action in actions"
          :key="action.label"
          class="w-full flex items-center gap-2.5 px-3 py-2 text-sm transition-colors cursor-pointer outline-none data-[highlighted]:bg-gray-50"
          :class="getActionClass(action.color)"
          @select="action.handler()"
        >
          <Icon :icon="action.icon" class="w-4 h-4 shrink-0" />
          <span>{{ action.label }}</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenuPortal>
  </DropdownMenuRoot>
</template>

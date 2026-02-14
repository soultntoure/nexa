<script setup lang="ts">
const props = withDefaults(defineProps<{
  variant?: 'default' | 'success' | 'warning' | 'destructive' | 'outline'
}>(), {
  variant: 'default',
})

const variantClasses: Record<string, string> = {
  default: 'bg-gray-100 text-gray-800',
  success: 'bg-green-50 text-green-700',
  warning: 'bg-amber-50 text-amber-700',
  destructive: 'bg-red-50 text-red-700',
  outline: 'border border-gray-200 text-gray-700',
}
</script>

<template>
  <span :class="['inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold', variantClasses[props.variant]]">
    <slot />
  </span>
</template>

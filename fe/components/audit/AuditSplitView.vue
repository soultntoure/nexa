<script setup lang="ts">
// Container for split-panel layout: left (40%) + right (60%)
// Uses slots for flexible content composition
</script>

<template>
  <div class="flex h-[28rem] shrink-0 gap-4 lg:flex-row flex-col">
    <div class="flex min-h-0 flex-1 flex-col overflow-y-auto rounded-xl border border-gray-200 bg-white p-4 lg:w-2/5">
      <slot name="left" />
    </div>
    <div class="flex min-h-0 flex-1 flex-col overflow-y-auto rounded-xl border border-gray-200 bg-white p-4 lg:w-3/5">
      <slot name="right" />
    </div>
  </div>
</template>

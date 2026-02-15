<script setup lang="ts">
</script>

<template>
  <div class="flex h-screen bg-gray-50">
    <AppSidebar />
    <main class="flex flex-1 flex-col overflow-hidden">
      <div class="flex flex-1 flex-col overflow-y-auto p-4">
        <slot />
      </div>
    </main>
    <Chatbot />
  </div>
</template>

<script setup lang="ts">
</script>

<template>
  <div class="flex h-screen bg-gray-50">
    <AppSidebar />
    <main class="flex flex-1 flex-col overflow-y-scroll">
      <div class="flex flex-1 flex-col p-6">
        <slot />
      </div>
    </main>
    <Chatbot />
  </div>
</template>

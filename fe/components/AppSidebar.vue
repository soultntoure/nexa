<script setup lang="ts">
import { Icon } from '@iconify/vue'

const route = useRoute()
const isOpen = ref(false)

const navItems = [
  { label: 'Dashboard', to: '/', icon: 'lucide:layout-grid' },
{ label: 'Withdrawal', to: '/withdrawal', icon: 'lucide:arrow-up-circle' },
  { label: 'Withdrawals', to: '/withdrawals', icon: 'lucide:list' },
  { label: 'Customers', to: '/customers', icon: 'lucide:users' },
  { label: 'Alerts', to: '/alerts', icon: 'lucide:bell' },
  { label: 'Audit', to: '/audit', icon: 'lucide:scan-search' },
  { label: 'NL Query', to: '/query', icon: 'lucide:message-square' },
  { label: 'Settings', to: '/settings', icon: 'lucide:settings' },
]

function isActive(to: string) {
  if (to === '/') return route.path === '/'
  return route.path === to || route.path.startsWith(to + '/')
}

function closeMobile() {
  isOpen.value = false
}
</script>

<template>
  <!-- Mobile hamburger -->
  <button
    class="fixed top-4 left-4 z-50 rounded-md bg-white p-2 shadow-md lg:hidden"
    @click="isOpen = !isOpen"
  >
    <Icon :icon="isOpen ? 'lucide:x' : 'lucide:menu'" class="h-6 w-6 text-gray-700" />
  </button>

  <!-- Mobile overlay -->
  <div
    v-if="isOpen"
    class="fixed inset-0 z-30 bg-black/40 lg:hidden"
    @click="closeMobile"
  />

  <!-- Sidebar -->
  <aside
    :class="[
      'fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-gray-200 bg-white transition-transform lg:static lg:translate-x-0',
      isOpen ? 'translate-x-0' : '-translate-x-full',
    ]"
  >
    <!-- Logo -->
    <div class="flex h-16 items-center gap-3 border-b border-gray-200 px-6">
      <img src="/nexa.svg" alt="Nexa" class="h-8 w-8" />
      <span class="text-xl font-bold text-gray-900">Nexa</span>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 space-y-1 px-3 py-4">
      <NuxtLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        :class="[
          'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
          isActive(item.to)
            ? 'bg-primary-50 text-primary-600'
            : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
        ]"
        @click="closeMobile"
      >
        <Icon :icon="item.icon" class="h-5 w-5 shrink-0" />
        {{ item.label }}
      </NuxtLink>
    </nav>

    <!-- Footer -->
    <div class="border-t border-gray-200 px-6 py-4">
      <p class="text-xs text-gray-400">Nexa v1.0</p>
    </div>
  </aside>
</template>

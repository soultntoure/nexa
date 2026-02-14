<script setup lang="ts">
import { Icon } from '@iconify/vue'

const route = useRoute()
const isOpen = ref(false)
const collapsed = ref(false)

const navItems = [
  { label: 'Dashboard', to: '/', icon: 'lucide:layout-grid' },
  { label: 'Withdrawal', to: '/withdrawal', icon: 'lucide:arrow-up-circle' },
  { label: 'Withdrawals', to: '/withdrawals', icon: 'lucide:list' },
  { label: 'Customers', to: '/customers', icon: 'lucide:users' },
  // { label: 'Alerts', to: '/alerts', icon: 'lucide:bell' },
  { label: 'Audit', to: '/audit', icon: 'lucide:scan-search' },
  // { label: 'NL Query', to: '/query', icon: 'lucide:message-square' },
  { label: 'Settings', to: '/settings', icon: 'lucide:settings' },
]

function isActive(to: string) {
  if (to === '/') return route.path === '/'
  return route.path === to || route.path.startsWith(to + '/')
}

function closeMobile() {
  isOpen.value = false
}

function toggleCollapse() {
  collapsed.value = !collapsed.value
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
      'fixed inset-y-0 left-0 z-40 flex flex-col border-r border-gray-200 bg-white transition-all duration-300 lg:static lg:translate-x-0',
      isOpen ? 'translate-x-0' : '-translate-x-full',
      collapsed ? 'w-[72px]' : 'w-64',
    ]"
  >
    <!-- Logo -->
    <div class="flex h-16 items-center border-b border-gray-200" :class="collapsed ? 'justify-center px-2' : 'gap-3 px-6'">
      <img src="/nexa.svg" alt="Nexa" class="h-8 w-8 shrink-0" />
      <span v-if="!collapsed" class="text-xl font-bold text-gray-900 whitespace-nowrap">Nexa</span>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 space-y-1 py-4" :class="collapsed ? 'px-2' : 'px-3'">
      <NuxtLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        :title="collapsed ? item.label : undefined"
        :class="[
          'group relative flex items-center rounded-lg py-2.5 text-sm font-medium transition-colors',
          collapsed ? 'justify-center px-2' : 'gap-3 px-3',
          isActive(item.to)
            ? 'bg-primary-50 text-primary-600'
            : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
        ]"
        @click="closeMobile"
      >
        <Icon :icon="item.icon" class="h-5 w-5 shrink-0" />
        <span v-if="!collapsed">{{ item.label }}</span>
        <!-- Tooltip on hover when collapsed -->
        <span
          v-if="collapsed"
          class="pointer-events-none absolute left-full ml-2 hidden rounded-md bg-gray-900 px-2 py-1 text-xs text-white whitespace-nowrap group-hover:block"
        >
          {{ item.label }}
        </span>
      </NuxtLink>
    </nav>

    <!-- Collapse toggle (desktop only) -->
    <div class="hidden border-t border-gray-200 lg:block" :class="collapsed ? 'px-2 py-3' : 'px-3 py-3'">
      <button
        :class="[
          'flex w-full items-center rounded-lg py-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700',
          collapsed ? 'justify-center px-2' : 'gap-3 px-3',
        ]"
        @click="toggleCollapse"
      >
        <Icon
          :icon="collapsed ? 'lucide:panel-right-close' : 'lucide:panel-left-close'"
          class="h-5 w-5 shrink-0"
        />
        <span v-if="!collapsed" class="text-sm font-medium">Collapse</span>
      </button>
    </div>

    <!-- Footer -->
    <div class="border-t border-gray-200 py-4" :class="collapsed ? 'px-2 text-center' : 'px-6'">
      <p class="text-xs text-gray-400">{{ collapsed ? 'v1.0' : 'Nexa v1.0' }}</p>
    </div>
  </aside>
</template>

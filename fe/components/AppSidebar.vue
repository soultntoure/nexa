<script setup lang="ts">
import { Icon } from '@iconify/vue'

const route = useRoute()
const isOpen = ref(false)
const collapsed = ref(false)

const navItems = [
  { label: 'Dashboard', to: '/', icon: '/icons/dashboard.svg', isCustom: true },
  { label: 'Withdrawals', to: '/withdrawals', icon: '/icons/withdrawal.svg', isCustom: true },
  { label: 'Customers', to: '/customers', icon: '/icons/profile.svg', isCustom: true },
  // { label: 'Alerts', to: '/alerts', icon: 'lucide:bell' },
  { label: 'Audit', to: '/audit', icon: '/icons/robot.svg', isCustom: true },
  // { label: 'NL Query', to: '/query', icon: 'lucide:message-square' },
  { label: 'Settings', to: '/settings', icon: '/icons/setting.svg', isCustom: true },
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
    <nav class="flex-1 space-y-1 py-4" :class="collapsed ? 'px-2' : 'px-4'">
      <TooltipProvider v-if="collapsed">
        <TooltipRoot v-for="item in navItems" :key="item.to">
          <TooltipTrigger as-child>
            <NuxtLink
              :to="item.to"
              :class="[
                'group relative flex items-center rounded-lg py-2.5 text-sm font-medium transition-colors',
                'justify-center px-2',
                isActive(item.to)
                  ? 'bg-primary-50 text-primary-600'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
              ]"
              @click="closeMobile"
            >
              <img v-if="item.isCustom" :src="item.icon" alt="" class="h-5 w-5 shrink-0" />
              <Icon v-else :icon="item.icon" class="h-5 w-5 shrink-0" />
            </NuxtLink>
          </TooltipTrigger>
          <TooltipPortal>
            <TooltipContent side="right" class="z-[1300] rounded bg-gray-900 px-2 py-1 text-xs text-white shadow-lg whitespace-nowrap" :side-offset="8">
              {{ item.label }}
              <TooltipArrow class="fill-gray-900" />
            </TooltipContent>
          </TooltipPortal>
        </TooltipRoot>
      </TooltipProvider>
      <template v-else>
        <NuxtLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          :class="[
            'group relative flex items-center justify-between rounded-lg py-2.5 px-3 text-sm font-medium transition-all',
            isActive(item.to)
              ? 'bg-gray-100 text-gray-900'
              : 'text-gray-500 hover:text-gray-700',
          ]"
          @click="closeMobile"
        >
          <div class="flex items-center gap-3">
            <img
              v-if="item.isCustom"
              :src="item.icon"
              alt=""
              :class="[
                'h-5 w-5 shrink-0',
                isActive(item.to) ? '' : 'opacity-60'
              ]"
              :style="isActive(item.to) ? 'filter: brightness(0) saturate(100%) invert(16%) sepia(99%) saturate(6995%) hue-rotate(345deg) brightness(102%) contrast(109%)' : ''"
            />
            <Icon
              v-else
              :icon="item.icon"
              :class="[
                'h-5 w-5 shrink-0',
                isActive(item.to) ? '' : 'text-gray-400'
              ]"
              :style="isActive(item.to) ? 'color: #FF003D' : ''"
            />
            <span>{{ item.label }}</span>
          </div>
          <Icon
            v-if="isActive(item.to)"
            icon="lucide:chevron-right"
            class="h-5 w-5 text-gray-400"
          />
        </NuxtLink>
      </template>
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

<script setup lang="ts">
import { Icon } from '@iconify/vue'

const isOpen = ref(false)
const dropdownRef = ref<HTMLElement | null>(null)

const notifications = ref([
  { id: 1, title: 'High-risk payout flagged', time: '2 min ago', read: false },
  { id: 2, title: 'Fraud pattern detected', time: '15 min ago', read: false },
  { id: 3, title: 'Bulk action completed', time: '1 hour ago', read: true },
])

const unreadCount = computed(() => notifications.value.filter(n => !n.read).length)

function toggle() {
  isOpen.value = !isOpen.value
}

function markRead(id: number) {
  const n = notifications.value.find(n => n.id === id)
  if (n) n.read = true
}

function handleClickOutside(e: MouseEvent) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div ref="dropdownRef" class="relative">
    <button
      class="relative rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
      @click="toggle"
    >
      <Icon icon="lucide:bell" class="h-5 w-5" />
      <span
        v-if="unreadCount > 0"
        class="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary-500 text-[10px] font-bold text-white"
      >
        {{ unreadCount }}
      </span>
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
        class="absolute right-0 mt-2 w-80 rounded-xl border border-gray-200 bg-white shadow-lg"
      >
        <div class="border-b border-gray-100 px-4 py-3">
          <h3 class="text-sm font-semibold text-gray-900">Notifications</h3>
        </div>
        <ul class="max-h-64 overflow-y-auto divide-y divide-gray-100">
          <li
            v-for="n in notifications"
            :key="n.id"
            :class="['cursor-pointer px-4 py-3 transition-colors hover:bg-gray-50', !n.read && 'bg-primary-50/40']"
            @click="markRead(n.id)"
          >
            <p class="text-sm font-medium text-gray-800">{{ n.title }}</p>
            <p class="mt-0.5 text-xs text-gray-400">{{ n.time }}</p>
          </li>
        </ul>
      </div>
    </Transition>
  </div>
</template>

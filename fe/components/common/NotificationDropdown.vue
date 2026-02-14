<script setup lang="ts">
import { Icon } from '@iconify/vue'

interface Notification {
  id: string
  title: string
  time: string
  read: boolean
  type: string
}

const isOpen = ref(false)
const dropdownRef = ref<HTMLElement | null>(null)
const notifications = ref<Notification[]>([])

let pollTimer: ReturnType<typeof setInterval> | null = null

const unreadCount = computed(() => notifications.value.filter(n => !n.read).length)

function toggle() {
  isOpen.value = !isOpen.value
}

async function markRead(id: string) {
  const n = notifications.value.find(n => n.id === id)
  if (!n || n.read) return
  n.read = true
  try {
    await $fetch('/api/alerts/read', {
      method: 'PATCH',
      body: { alert_ids: [id] },
    })
  } catch {
    // optimistic update already applied
  }
}

async function markAllRead() {
  const unreadIds = notifications.value.filter(n => !n.read).map(n => n.id)
  if (!unreadIds.length) return
  notifications.value.forEach(n => { n.read = true })
  try {
    await $fetch('/api/alerts/read', {
      method: 'PATCH',
      body: { alert_ids: unreadIds },
    })
  } catch {
    // optimistic update already applied
  }
}

function handleClickOutside(e: MouseEvent) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target as Node)) {
    isOpen.value = false
  }
}

async function fetchNotifications() {
  try {
    const data = await $fetch<{ alerts: any[] }>('/api/alerts')
    const recent = (data.alerts ?? []).slice(0, 8)
    notifications.value = recent.map(a => ({
      id: a.id,
      title: a.type === 'card_lockdown'
        ? `Card lockdown: ${a.customer_name}`
        : a.type === 'block'
          ? `Blocked: ${a.customer_name}`
          : `Escalated: ${a.customer_name}`,
      time: relativeTime(a.timestamp),
      read: a.read,
      type: a.type,
    }))
  } catch {
    // keep existing notifications on error
  }
}

function relativeTime(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  fetchNotifications()
  pollTimer = setInterval(fetchNotifications, 5000)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  if (pollTimer) clearInterval(pollTimer)
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
        {{ unreadCount > 9 ? '9+' : unreadCount }}
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
        <div class="flex items-center justify-between border-b border-gray-100 px-4 py-3">
          <h3 class="text-sm font-semibold text-gray-900">Notifications</h3>
          <button
            v-if="unreadCount > 0"
            class="text-xs font-medium text-primary-500 hover:text-primary-700"
            @click.stop="markAllRead"
          >
            Mark all read
          </button>
        </div>
        <ul class="max-h-72 overflow-y-auto divide-y divide-gray-100">
          <li
            v-for="n in notifications"
            :key="n.id"
            :class="['cursor-pointer px-4 py-3 transition-colors hover:bg-gray-50', !n.read && 'bg-primary-50/40']"
            @click="markRead(n.id)"
          >
            <div class="flex items-start gap-2.5">
              <span v-if="!n.read" class="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-primary-500" />
              <span v-else class="mt-1.5 h-2 w-2 shrink-0" />
              <Icon
                :icon="n.type === 'card_lockdown' ? 'lucide:credit-card' : n.type === 'block' ? 'lucide:shield-off' : 'lucide:alert-triangle'"
                class="mt-0.5 h-4 w-4 shrink-0"
                :class="n.type === 'card_lockdown' ? 'text-orange-500' : n.type === 'block' ? 'text-red-500' : 'text-amber-500'"
              />
              <div>
                <p :class="['text-sm text-gray-800', !n.read ? 'font-semibold' : 'font-medium']">{{ n.title }}</p>
                <p class="mt-0.5 text-xs text-gray-400">{{ n.time }}</p>
              </div>
            </div>
          </li>
          <li v-if="!notifications.length" class="px-4 py-6 text-center text-sm text-gray-400">
            No notifications
          </li>
        </ul>
      </div>
    </Transition>
  </div>
</template>

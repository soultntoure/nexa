<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { WithdrawalDiscussionContext } from '~/composables/useWithdrawalDiscussion'
import type { ChartSpec } from '~/utils/chartTransformer'
import type { QueryMessage } from '~/components/query/QueryMessageBubble.vue'

useHead({ title: 'NL Query - Nexa' })

const input = ref('')
const isLoading = ref(false)
const isStreaming = ref(false)
const messagesContainer = ref<HTMLElement>()
const inputBar = ref<InstanceType<typeof import('~/components/query/QueryInputBar.vue').default>>()
const messages = ref<QueryMessage[]>([])
const queryHistory = ref<string[]>([])
const showHistory = ref(false)
const sessionId = ref(generateId())
const visualize = true
const route = useRoute()
const { discussionContext, clearDiscussionContext, buildDiscussionPrompt } = useWithdrawalDiscussion()
const typewriter = useTypewriter()

const DISCUSSION_QUERY_KEYS = [
  'focus', 'id', 'withdrawal_id', 'customer_external_id', 'customer_name',
  'customer_email', 'amount', 'currency', 'risk_score', 'risk_level',
  'status', 'payment_method', 'recipient_name', 'recipient_account',
  'ip_address', 'device', 'created_at',
] as const

const routeDiscussionContext = computed<WithdrawalDiscussionContext | null>(() => {
  const withdrawalId = toQueryString(route.query.withdrawal_id)
  if (!withdrawalId) return null
  return {
    id: toQueryString(route.query.id) || withdrawalId,
    withdrawal_id: withdrawalId,
    customer_external_id: toQueryString(route.query.customer_external_id),
    customer_name: toQueryString(route.query.customer_name),
    customer_email: toQueryString(route.query.customer_email),
    amount: toQueryNumber(route.query.amount),
    currency: toQueryString(route.query.currency) || 'USD',
    risk_score: toQueryNumber(route.query.risk_score),
    risk_level: toQueryString(route.query.risk_level) || 'medium',
    status: toQueryString(route.query.status) || 'pending',
    payment_method: toQueryString(route.query.payment_method),
    recipient_name: toQueryString(route.query.recipient_name),
    recipient_account: toQueryString(route.query.recipient_account),
    ip_address: toQueryString(route.query.ip_address),
    device: toQueryString(route.query.device),
    created_at: toQueryString(route.query.created_at) || new Date().toISOString(),
  }
})

const activeContext = computed(() => discussionContext.value ?? routeDiscussionContext.value)
const contextLabel = computed(() => {
  const ctx = activeContext.value
  if (!ctx) return ''
  return ctx.customer_name || ctx.customer_external_id || 'Withdrawal'
})
const hasTableData = computed(() => messages.value.some(m => m.role === 'assistant' && m.data?.table))

// Wire typewriter displayed text to the active assistant message
const activeAssistantId = ref<string | null>(null)
const hasReceivedTokens = ref(false)

function getDisplayedContent(msg: QueryMessage): string {
  if (msg.role !== 'assistant') return msg.content
  if (msg.id === activeAssistantId.value) return typewriter.displayed.value
  return msg.content
}

function isActiveBubble(msg: QueryMessage): boolean {
  return msg.id === activeAssistantId.value && isStreaming.value
}

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2)
}

function toQueryString(value: string | null | (string | null)[] | undefined): string {
  if (Array.isArray(value)) return String(value[0] ?? '')
  return String(value ?? '')
}

function toQueryNumber(value: string | null | (string | null)[] | undefined): number {
  const parsed = Number(toQueryString(value))
  return Number.isFinite(parsed) ? parsed : 0
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// Keep scrolling as typewriter drains characters
watch(() => typewriter.displayed.value, scrollToBottom)

async function sendQuery(queryText?: string) {
  const q = queryText || input.value.trim()
  if (!q || isLoading.value) return
  const ctx = activeContext.value
  const llmQuestion = ctx ? buildContextualQuestion(q, ctx) : q

  input.value = ''

  messages.value.push({
    id: generateId(), role: 'user', content: q,
    timestamp: new Date(), sqlQueries: [], showSql: false, showChart: false,
  })

  queryHistory.value.unshift(q)
  if (queryHistory.value.length > 20) queryHistory.value.pop()

  scrollToBottom()
  isLoading.value = true
  isStreaming.value = true

  const assistantMsg: QueryMessage = {
    id: generateId(), role: 'assistant', content: '',
    timestamp: new Date(), sqlQueries: [], showSql: false, showChart: false,
  }
  messages.value.push(assistantMsg)
  activeAssistantId.value = assistantMsg.id
  typewriter.reset()

  try {
    const response = await fetch('/api/query/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: llmQuestion, session_id: sessionId.value, visualize }),
    })
    if (!response.ok || !response.body) throw new Error('Stream failed')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    hasReceivedTokens.value = false

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const event = JSON.parse(line.slice(6))
          handleSSEEvent(event, assistantMsg)
        } catch { /* skip malformed */ }
      }
    }
    if (buffer.startsWith('data: ')) {
      try { handleSSEEvent(JSON.parse(buffer.slice(6)), assistantMsg) } catch { /* skip */ }
    }

    // Flush remaining typewriter queue and sync content
    typewriter.flush()
    assistantMsg.content = typewriter.displayed.value

    if (!assistantMsg.content) {
      assistantMsg.content = 'No response received. Please try again.'
    }
  } catch {
    typewriter.flush()
    assistantMsg.content = typewriter.displayed.value || 'Connection failed. Please check the server and try again.'
  } finally {
    isLoading.value = false
    isStreaming.value = false
    activeAssistantId.value = null
    scrollToBottom()
    nextTick(() => inputBar.value?.focus())
  }
}

function normalizeChartSpec(raw: unknown): ChartSpec | null {
  if (!raw || typeof raw !== 'object') return null
  const r = raw as Record<string, unknown>
  if (!r.chart_type || !r.x_key || !Array.isArray(r.series) || !Array.isArray(r.rows)) return null
  if (!r.rows.length) return null
  return r as unknown as ChartSpec
}

function handleSSEEvent(event: { type: string; [key: string]: unknown }, msg: QueryMessage) {
  switch (event.type) {
    case 'token':
      hasReceivedTokens.value = true
      typewriter.push(event.content as string)
      break
    case 'tool_start':
      msg.sqlQueries.push({ sql: event.preview as string, result: '' })
      break
    case 'tool_end': {
      const latest = msg.sqlQueries.at(-1)
      if (latest) latest.result = event.result as string
      break
    }
    case 'chart': {
      const spec = normalizeChartSpec(event.chart)
      if (spec) { msg.chart = spec; scrollToBottom() }
      break
    }
    case 'answer':
      // Only push full answer as fallback when NO tokens were streamed
      if (!hasReceivedTokens.value && event.content) {
        typewriter.push(event.content as string)
      }
      break
    case 'error':
      typewriter.flush()
      msg.content = `Error: ${event.message}`
      scrollToBottom()
      break
  }
}

function exportResults() {
  const last = messages.value.filter(m => m.role === 'assistant' && m.data?.table).at(-1)
  const table = last?.data?.table
  if (!table) return
  const csv = [table.headers.join(','), ...table.rows.map(r => r.join(','))].join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = 'query-results.csv'; a.click()
  URL.revokeObjectURL(url)
}

function clearChat() {
  messages.value = []
  sessionId.value = generateId()
  typewriter.reset()
}

async function dismissContext() {
  clearDiscussionContext()
  const nextQuery: Record<string, string | string[]> = { ...(route.query as Record<string, string | string[]>) }
  for (const key of DISCUSSION_QUERY_KEYS) delete nextQuery[key]
  await navigateTo({ path: '/query', query: nextQuery }, { replace: true })
}

function buildContextualQuestion(question: string, context: WithdrawalDiscussionContext): string {
  return [question, '', '---', 'Hidden withdrawal context (do not repeat verbatim unless asked):', buildDiscussionPrompt(context)].join('\n')
}
</script>

<template>
  <div class="flex h-[calc(100vh-5rem)] flex-col">
    <!-- Header -->
    <QueryHeader
      :has-table-data="hasTableData"
      :has-messages="messages.length > 0"
      :show-history="showHistory"
      @toggle-history="showHistory = !showHistory"
      @export-results="exportResults"
      @clear-chat="clearChat"
    />

    <!-- Context chip — minimal pill -->
    <div v-if="activeContext" class="mb-3 flex items-center gap-2">
      <span class="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
        <Icon icon="lucide:user" class="h-3 w-3" />
        {{ contextLabel }}
        <button class="ml-1 rounded-full p-0.5 hover:bg-blue-200/60" @click="dismissContext">
          <Icon icon="lucide:x" class="h-3 w-3" />
        </button>
      </span>
    </div>

    <div class="flex flex-1 gap-4 overflow-hidden">
      <!-- History Sidebar -->
      <Transition
        enter-active-class="transition ease-out duration-200"
        enter-from-class="-translate-x-full opacity-0"
        enter-to-class="translate-x-0 opacity-100"
        leave-active-class="transition ease-in duration-150"
        leave-from-class="translate-x-0 opacity-100"
        leave-to-class="-translate-x-full opacity-0"
      >
        <div v-if="showHistory" class="w-64 shrink-0 overflow-y-auto rounded-xl border border-gray-200 bg-white p-4">
          <h3 class="mb-3 text-sm font-semibold text-gray-700">Query History</h3>
          <div v-if="queryHistory.length === 0" class="text-center text-xs text-gray-400 py-8">
            No queries yet
          </div>
          <div v-else class="space-y-1">
            <button
              v-for="(q, i) in queryHistory"
              :key="i"
              class="block w-full truncate rounded-lg px-3 py-2 text-left text-sm text-gray-600 hover:bg-gray-50"
              @click="sendQuery(q)"
            >
              {{ q }}
            </button>
          </div>
        </div>
      </Transition>

      <!-- Chat Area -->
      <div class="flex flex-1 flex-col overflow-hidden rounded-xl border border-gray-200 bg-white">
        <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4 space-y-4">
          <QueryEmptyState v-if="messages.length === 0" @select="sendQuery" />

          <template v-else>
            <QueryMessageBubble
              v-for="msg in messages"
              :key="msg.id"
              :msg="msg"
              :displayed-content="getDisplayedContent(msg)"
              :is-active="isActiveBubble(msg)"
              :is-animating="isActiveBubble(msg) && typewriter.isAnimating.value"
            />

          </template>
        </div>

        <QueryInputBar ref="inputBar" v-model="input" :disabled="isLoading" @submit="sendQuery()" />
      </div>
    </div>
  </div>
</template>

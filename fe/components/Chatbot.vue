<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { ChartSpec } from '~/utils/chartTransformer'
import type { QueryMessage } from '~/components/query/QueryMessageBubble.vue'

const { isOpen, messages, sessionId, widgetContext, toggle, close, clearChat, dismissContext, generateId } = useChatWidgetState()
const { buildDiscussionPrompt } = useWithdrawalDiscussion()

const input = ref('')
const isLoading = ref(false)
const isStreaming = ref(false)
const messagesContainer = ref<{ $el: HTMLElement }>()
const inputBar = ref<InstanceType<typeof import('~/components/query/QueryInputBar.vue').default>>()
const typewriter = useTypewriter()
const visualize = true

const route = useRoute()
const isQueryPage = computed(() => route.path === '/query')

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

function scrollToBottom() {
  nextTick(() => {
    const el = messagesContainer.value?.$el
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  })
}

watch(() => typewriter.displayed.value, scrollToBottom)

watch(isOpen, (open) => {
  if (open) {
    scrollToBottom()
    nextTick(() => inputBar.value?.focus())

    // Auto-send initial query when opened with withdrawal context and no messages yet
    if (widgetContext.value && messages.value.length === 0) {
      const ctx = widgetContext.value
      const autoQuery = `Analyze this withdrawal for ${ctx.customer_name} — $${ctx.amount.toLocaleString()} ${ctx.currency}, risk score ${ctx.risk_score.toFixed(2)} (${ctx.risk_level}). What are the key red flags and what should I verify?`
      nextTick(() => sendQuery(autoQuery))
    }
  }
})

const contextLabel = computed(() => {
  const ctx = widgetContext.value
  if (!ctx) return ''
  return ctx.customer_name || ctx.customer_external_id || 'Withdrawal'
})

function buildContextualQuestion(question: string): string {
  const ctx = widgetContext.value
  if (!ctx) return question
  return [question, '', '---', 'Hidden withdrawal context (do not repeat verbatim unless asked):', buildDiscussionPrompt(ctx)].join('\n')
}

async function sendQuery(queryText?: string) {
  const q = queryText || input.value.trim()
  if (!q || isLoading.value) return

  const llmQuestion = buildContextualQuestion(q)
  input.value = ''

  messages.value.push({
    id: generateId(), role: 'user', content: q,
    timestamp: new Date(), sqlQueries: [], showSql: false, showChart: false,
  })

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

function handleClear() {
  clearChat()
  typewriter.reset()
}
</script>

<template>
  <Teleport to="body">
    <div v-if="!isQueryPage" class="fixed bottom-6 right-6 z-[1050]">
      <!-- Chat Panel (popup above FAB) -->
      <Transition
        enter-active-class="transition ease-out duration-300 origin-bottom-right"
        enter-from-class="translate-y-4 opacity-0 scale-95"
        enter-to-class="translate-y-0 opacity-100 scale-100"
        leave-active-class="transition ease-in duration-200 origin-bottom-right"
        leave-from-class="translate-y-0 opacity-100 scale-100"
        leave-to-class="translate-y-4 opacity-0 scale-95"
      >
        <div
          v-if="isOpen"
          class="absolute bottom-16 right-0 mb-2 flex flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl w-[calc(100vw-3rem)] sm:w-[400px]"
          style="height: min(600px, 80vh)"
        >
          <!-- Header -->
          <div class="flex items-center justify-between bg-primary-600 px-4 py-3">
            <div class="flex items-center gap-2">
              <div class="flex h-8 w-8 items-center justify-center rounded-full bg-white/20">
                <Icon icon="lucide:bot" class="h-4 w-4 text-white" />
              </div>
              <div>
                <h3 class="text-sm font-semibold text-white">Nexa AI</h3>
                <p class="text-xs text-primary-100">Ask anything about your data</p>
              </div>
            </div>
            <div class="flex items-center gap-1">
              <TooltipProvider>
                <TooltipRoot v-if="messages.length > 0">
                  <TooltipTrigger as-child>
                    <button
                      class="rounded-lg p-1.5 text-white/70 transition-colors hover:bg-white/10 hover:text-white"
                      @click="handleClear"
                    >
                      <Icon icon="lucide:trash-2" class="h-4 w-4" />
                    </button>
                  </TooltipTrigger>
                  <TooltipPortal>
                    <TooltipContent class="z-[1300] rounded bg-gray-900 px-2 py-1 text-xs text-white shadow-lg" :side-offset="5">
                      Clear chat
                      <TooltipArrow class="fill-gray-900" />
                    </TooltipContent>
                  </TooltipPortal>
                </TooltipRoot>
                <TooltipRoot>
                  <TooltipTrigger as-child>
                    <button
                      class="rounded-lg p-1.5 text-white/70 transition-colors hover:bg-white/10 hover:text-white"
                      @click="close"
                    >
                      <Icon icon="lucide:x" class="h-4 w-4" />
                    </button>
                  </TooltipTrigger>
                  <TooltipPortal>
                    <TooltipContent class="z-[1300] rounded bg-gray-900 px-2 py-1 text-xs text-white shadow-lg" :side-offset="5">
                      Close
                      <TooltipArrow class="fill-gray-900" />
                    </TooltipContent>
                  </TooltipPortal>
                </TooltipRoot>
              </TooltipProvider>
            </div>
          </div>

          <!-- Context chip -->
          <div v-if="widgetContext" class="flex items-center gap-2 border-b border-gray-100 px-4 py-2 bg-blue-50/50">
            <span class="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
              <Icon icon="lucide:user" class="h-3 w-3" />
              {{ contextLabel }}
              <button class="ml-0.5 rounded-full p-0.5 hover:bg-blue-200/60" @click="dismissContext">
                <Icon icon="lucide:x" class="h-2.5 w-2.5" />
              </button>
            </span>
          </div>

          <!-- Messages -->
          <ScrollAreaRoot class="flex-1 overflow-hidden">
            <ScrollAreaViewport ref="messagesContainer" class="h-full w-full p-4 space-y-4">
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
            </ScrollAreaViewport>
            <ScrollAreaScrollbar orientation="vertical" class="flex touch-none select-none bg-transparent p-0.5 transition-colors hover:bg-gray-800/50 data-[orientation=vertical]:w-2">
              <ScrollAreaThumb class="relative flex-1 rounded-full bg-gray-600 hover:bg-gray-500" />
            </ScrollAreaScrollbar>
          </ScrollAreaRoot>

          <!-- Input -->
          <QueryInputBar ref="inputBar" v-model="input" :disabled="isLoading" @submit="sendQuery()" />
        </div>
      </Transition>

      <!-- FAB Button (always visible, toggles panel) -->
      <button
        class="flex h-14 w-14 items-center justify-center rounded-full bg-primary-600 text-white shadow-lg transition-all hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        :aria-label="isOpen ? 'Close chat' : 'Open chat'"
        @click="toggle"
      >
        <Icon :icon="isOpen ? 'lucide:x' : 'lucide:message-square'" class="h-6 w-6 transition-transform" />
      </button>
    </div>
  </Teleport>
</template>

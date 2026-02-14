<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })

useHead({ title: 'NL Query - Nexa' })

interface SqlQuery {
  sql: string
  result: string
}

interface QueryMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sqlQueries: SqlQuery[]
  showSql: boolean
  data?: {
    summary?: string
    table?: { headers: string[]; rows: string[][] }
    actions?: { label: string; link: string }[]
  }
}

const input = ref('')
const isLoading = ref(false)
const isStreaming = ref(false)
const messagesContainer = ref<HTMLElement>()
const inputEl = ref<HTMLInputElement>()
const messages = ref<QueryMessage[]>([])
const queryHistory = ref<string[]>([])
const showHistory = ref(false)
const sessionId = ref(generateId())

const exampleQueries = [
  'Show me accounts that deposited but traded minimally',
  'Which customers have multiple payment methods from different countries?',
  'Find velocity abuse patterns in the last 7 days',
  "What's our auto-approval rate this week?",
]

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2)
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

async function sendQuery(queryText?: string) {
  const q = queryText || input.value.trim()
  if (!q || isLoading.value) return

  input.value = ''

  const userMsg: QueryMessage = {
    id: generateId(),
    role: 'user',
    content: q,
    timestamp: new Date(),
    sqlQueries: [],
    showSql: false,
  }
  messages.value.push(userMsg)

  if (!queryHistory.value.includes(q)) {
    queryHistory.value.unshift(q)
    if (queryHistory.value.length > 20) queryHistory.value.pop()
  }

  scrollToBottom()
  isLoading.value = true
  isStreaming.value = true

  // Create a placeholder assistant message for streaming tokens into
  const assistantMsg: QueryMessage = {
    id: generateId(),
    role: 'assistant',
    content: '',
    timestamp: new Date(),
    sqlQueries: [],
    showSql: false,
  }
  messages.value.push(assistantMsg)

  try {
    const response = await fetch('/api/query/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q, session_id: sessionId.value }),
    })

    if (!response.ok || !response.body) throw new Error('Stream failed')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

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
        } catch { /* skip malformed lines */ }
      }
    }

    // Process remaining buffer
    if (buffer.startsWith('data: ')) {
      try {
        const event = JSON.parse(buffer.slice(6))
        handleSSEEvent(event, assistantMsg)
      } catch { /* skip */ }
    }

    if (!assistantMsg.content) {
      assistantMsg.content = 'No response received. Please try again.'
    }
  } catch {
    assistantMsg.content = 'Connection failed. Please check the server and try again.'
  } finally {
    isLoading.value = false
    isStreaming.value = false
    scrollToBottom()
    nextTick(() => inputEl.value?.focus())
  }
}

function handleSSEEvent(event: { type: string; [key: string]: unknown }, msg: QueryMessage) {
  switch (event.type) {
    case 'token':
      msg.content += event.content as string
      scrollToBottom()
      break
    case 'tool_start':
      msg.sqlQueries.push({ sql: event.preview as string, result: '' })
      break
    case 'tool_end':
      if (msg.sqlQueries.length > 0) {
        msg.sqlQueries[msg.sqlQueries.length - 1].result = event.result as string
      }
      break
    case 'answer':
      // Only use full answer if no tokens were streamed (fallback)
      if (!msg.content && event.content) msg.content = event.content as string
      scrollToBottom()
      break
    case 'error':
      msg.content = `Error: ${event.message}`
      scrollToBottom()
      break
  }
}

function exportResults() {
  const assistantMessages = messages.value.filter(m => m.role === 'assistant' && m.data?.table)
  if (assistantMessages.length === 0) return

  const lastTable = assistantMessages[assistantMessages.length - 1].data!.table!
  const csv = [lastTable.headers.join(','), ...lastTable.rows.map(r => r.join(','))].join('\n')

  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'query-results.csv'
  a.click()
  URL.revokeObjectURL(url)
}

function clearChat() {
  messages.value = []
  sessionId.value = generateId()
}

function formatTime(date: Date) {
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}

</script>

<template>
  <div class="flex h-[calc(100vh-5rem)] flex-col">
    <!-- Header -->
    <div class="mb-4 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Natural Language Query</h1>
        <p class="mt-1 text-sm text-gray-500">Ask questions about your payment data using AI</p>
      </div>
      <div class="flex items-center gap-2">
        <button
          class="flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
          @click="showHistory = !showHistory"
        >
          <Icon icon="lucide:history" class="h-4 w-4" />
          History
        </button>
        <button
          v-if="messages.some(m => m.data?.table)"
          class="flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
          @click="exportResults"
        >
          <Icon icon="lucide:download" class="h-4 w-4" />
          Export
        </button>
        <button
          v-if="messages.length > 0"
          class="flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
          @click="clearChat"
        >
          <Icon icon="lucide:trash-2" class="h-4 w-4" />
          Clear
        </button>
      </div>
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
        <!-- Messages -->
        <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4 space-y-4">
          <!-- Empty state -->
          <div v-if="messages.length === 0" class="flex h-full flex-col items-center justify-center">
            <div class="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-50">
              <Icon icon="lucide:message-square" class="h-8 w-8 text-primary-500" />
            </div>
            <h2 class="text-lg font-semibold text-gray-800">Ask anything about your data</h2>
            <p class="mt-1 text-sm text-gray-500">Use natural language to query transactions, detect fraud, and analyze patterns</p>

            <div class="mt-6 grid grid-cols-1 gap-2 sm:grid-cols-2">
              <button
                v-for="example in exampleQueries"
                :key="example"
                class="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-left text-sm text-gray-600 transition-all hover:border-primary-300 hover:bg-primary-50 hover:text-primary-700"
                @click="sendQuery(example)"
              >
                <Icon icon="lucide:sparkles" class="mb-1 h-4 w-4 text-primary-400" />
                <span class="block">{{ example }}</span>
              </button>
            </div>
          </div>

          <!-- Message bubbles -->
          <template v-else>
            <div
              v-for="msg in messages"
              :key="msg.id"
              :class="['flex', msg.role === 'user' ? 'justify-end' : 'justify-start']"
            >
              <div :class="['max-w-[80%]', msg.role === 'user' ? '' : 'w-full max-w-2xl']">
                <!-- User message -->
                <div v-if="msg.role === 'user'" class="rounded-2xl rounded-br-md bg-primary-600 px-4 py-3 text-sm text-white">
                  {{ msg.content }}
                  <p class="mt-1 text-[10px] text-primary-200">{{ formatTime(msg.timestamp) }}</p>
                </div>

                <!-- Assistant message -->
                <div v-else-if="msg.content" class="space-y-3">
                  <div class="flex items-start gap-2">
                    <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gray-100">
                      <Icon icon="lucide:bot" class="h-4 w-4 text-gray-600" />
                    </div>
                    <div class="rounded-2xl rounded-tl-md border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 shadow-sm">
                      <div class="prose prose-sm prose-gray max-w-none" v-html="marked.parse(msg.content || '')" />
                      <span v-if="isStreaming && msg === messages[messages.length - 1]" class="inline-block w-2 h-4 ml-0.5 bg-primary-500 animate-pulse rounded-sm" />
                      <p class="mt-1 text-[10px] text-gray-400">{{ formatTime(msg.timestamp) }}</p>
                    </div>
                  </div>

                  <!-- SQL Queries (collapsible) -->
                  <div v-if="msg.sqlQueries.length > 0" class="ml-9">
                    <button
                      class="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
                      @click="msg.showSql = !msg.showSql"
                    >
                      <Icon :icon="msg.showSql ? 'lucide:chevron-down' : 'lucide:chevron-right'" class="h-3 w-3" />
                      <Icon icon="lucide:database" class="h-3 w-3" />
                      {{ msg.sqlQueries.length }} SQL {{ msg.sqlQueries.length === 1 ? 'query' : 'queries' }} executed
                    </button>
                    <div v-if="msg.showSql" class="mt-2 space-y-2">
                      <div
                        v-for="(sq, si) in msg.sqlQueries"
                        :key="si"
                        class="rounded-lg border border-gray-200 bg-gray-900 text-gray-100 text-xs overflow-hidden"
                      >
                        <div class="flex items-center justify-between border-b border-gray-700 bg-gray-800 px-3 py-1.5">
                          <span class="font-mono text-[10px] text-gray-400">Query {{ si + 1 }}</span>
                          <span class="rounded bg-emerald-900 px-1.5 py-0.5 text-[10px] text-emerald-300">SQL</span>
                        </div>
                        <pre class="p-3 overflow-x-auto font-mono leading-relaxed"><code>{{ sq.sql }}</code></pre>
                        <div v-if="sq.result" class="border-t border-gray-700 bg-gray-800/50 p-3">
                          <span class="text-[10px] font-medium text-gray-400 uppercase tracking-wider">Result</span>
                          <pre class="mt-1 overflow-x-auto font-mono text-gray-300 leading-relaxed">{{ sq.result }}</pre>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Data table -->
                  <div v-if="msg.data?.table" class="ml-9 overflow-x-auto rounded-lg border border-gray-200">
                    <table class="w-full text-sm">
                      <thead>
                        <tr class="border-b border-gray-200 bg-gray-50">
                          <th
                            v-for="h in msg.data.table.headers"
                            :key="h"
                            class="px-3 py-2 text-left text-xs font-semibold text-gray-500"
                          >
                            {{ h }}
                          </th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-gray-100">
                        <tr v-for="(row, ri) in msg.data.table.rows" :key="ri" class="hover:bg-gray-50">
                          <td v-for="(cell, ci) in row" :key="ci" class="px-3 py-2 text-gray-700">
                            {{ cell }}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <!-- Action links -->
                  <div v-if="msg.data?.actions?.length" class="ml-9 flex flex-wrap gap-2">
                    <NuxtLink
                      v-for="action in msg.data.actions"
                      :key="action.label"
                      :to="action.link"
                      class="flex items-center gap-1 rounded-lg border border-primary-200 bg-primary-50 px-3 py-1.5 text-xs font-medium text-primary-700 hover:bg-primary-100"
                    >
                      <Icon icon="lucide:external-link" class="h-3 w-3" />
                      {{ action.label }}
                    </NuxtLink>
                  </div>
                </div>
              </div>
            </div>

            <!-- Typing indicator (only before first token arrives) -->
            <div v-if="isLoading && messages[messages.length - 1]?.role === 'assistant' && !messages[messages.length - 1]?.content" class="flex items-start gap-2">
              <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gray-100">
                <Icon icon="lucide:bot" class="h-4 w-4 text-gray-600" />
              </div>
              <div class="rounded-2xl rounded-tl-md border border-gray-200 bg-white px-4 py-3 shadow-sm">
                <div class="flex items-center gap-1.5 text-xs text-gray-500">
                  <span class="h-2 w-2 animate-bounce rounded-full bg-gray-400" style="animation-delay: 0ms" />
                  <span class="h-2 w-2 animate-bounce rounded-full bg-gray-400" style="animation-delay: 150ms" />
                  <span class="h-2 w-2 animate-bounce rounded-full bg-gray-400" style="animation-delay: 300ms" />
                  <span class="ml-1">Analyzing...</span>
                </div>
              </div>
            </div>
          </template>
        </div>

        <!-- Input bar -->
        <div class="border-t border-gray-200 p-4">
          <form class="flex items-center gap-3" @submit.prevent="sendQuery()">
            <input
              ref="inputEl"
              v-model="input"
              type="text"
              placeholder="Ask about fraud patterns, account behavior, or transactions..."
              class="flex-1 rounded-xl border border-gray-300 px-4 py-3 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500"
              :disabled="isLoading"
            />
            <button
              type="submit"
              class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary-600 text-white transition-colors hover:bg-primary-700 disabled:opacity-50"
              :disabled="!input.trim() || isLoading"
            >
              <Icon icon="lucide:send" class="h-5 w-5" />
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

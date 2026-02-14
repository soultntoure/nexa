<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { marked } from 'marked'
import type { ChartSpec } from '~/utils/chartTransformer'

export interface SqlQuery {
  sql: string
  result: string
}

export interface QueryMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sqlQueries: SqlQuery[]
  showSql: boolean
  showChart: boolean
  chart?: ChartSpec | null
  data?: {
    summary?: string
    table?: { headers: string[]; rows: string[][] }
    actions?: { label: string; link: string }[]
  }
}

const props = defineProps<{
  msg: QueryMessage
  displayedContent: string
  isActive: boolean
  isAnimating: boolean
}>()

function formatTime(date: Date) {
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div :class="['flex', msg.role === 'user' ? 'justify-end' : 'justify-start']">
    <div :class="['max-w-[80%]', msg.role === 'user' ? '' : 'w-full max-w-2xl']">
      <!-- User message -->
      <div v-if="msg.role === 'user'" class="rounded-2xl rounded-br-md bg-primary-600 px-4 py-3 text-sm text-white">
        {{ msg.content }}
        <p class="mt-1 text-[10px] text-primary-200">{{ formatTime(msg.timestamp) }}</p>
      </div>

      <!-- Assistant message -->
      <div v-else class="space-y-3">
        <div class="flex items-start gap-2">
          <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gray-100">
            <Icon icon="lucide:bot" class="h-4 w-4 text-gray-600" />
          </div>
          <div class="rounded-2xl rounded-tl-md border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 shadow-sm">
            <!-- Typing indicator (before any content arrives) -->
            <div v-if="isActive && !displayedContent" class="flex items-center gap-1.5 text-xs text-gray-500">
              <span class="h-2 w-2 animate-bounce rounded-full bg-gray-400" style="animation-delay: 0ms" />
              <span class="h-2 w-2 animate-bounce rounded-full bg-gray-400" style="animation-delay: 150ms" />
              <span class="h-2 w-2 animate-bounce rounded-full bg-gray-400" style="animation-delay: 300ms" />
              <span class="ml-1">Analyzing...</span>
            </div>
            <template v-else>
              <div
                v-if="displayedContent"
                class="prose prose-sm prose-gray max-w-none"
                v-html="marked.parse(displayedContent)"
              />
              <span
                v-if="isActive && isAnimating"
                class="inline-block w-2 h-4 ml-0.5 bg-primary-500 animate-pulse rounded-sm"
              />
              <p class="mt-1 text-[10px] text-gray-400">{{ formatTime(msg.timestamp) }}</p>
            </template>
          </div>
        </div>

        <!-- SQL Queries -->
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

        <!-- Visualization -->
        <div v-if="msg.chart" class="ml-9">
          <button
            class="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
            @click="msg.showChart = !msg.showChart"
          >
            <Icon :icon="msg.showChart ? 'lucide:chevron-down' : 'lucide:chevron-right'" class="h-3 w-3" />
            <Icon icon="lucide:chart-column" class="h-3 w-3" />
            Visualization result
          </button>
          <ChatPlotCard v-if="msg.showChart" :chart="msg.chart" class="mt-2" />
        </div>

        <!-- Data table -->
        <div v-if="msg.data?.table" class="ml-9 overflow-x-auto rounded-lg border border-gray-200">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-gray-200 bg-gray-50">
                <th v-for="h in msg.data.table.headers" :key="h" class="px-3 py-2 text-left text-xs font-semibold text-gray-500">
                  {{ h }}
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="(row, ri) in msg.data.table.rows" :key="ri" class="hover:bg-gray-50">
                <td v-for="(cell, ci) in row" :key="ci" class="px-3 py-2 text-gray-700">{{ cell }}</td>
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
</template>

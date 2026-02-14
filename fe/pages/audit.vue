<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { CandidateResult } from '~/utils/auditTypes'

useHead({ title: 'Audit - Nexa' })

interface RunListItem {
  run_id: string
  status: string
  started_at: string
  counters: {
    candidates?: number
    candidates_generated?: number
  }
}

const {
  runId, status, phases, clusters, candidates,
  selectedClusterId, selectedCandidateId, error,
  triggerRun, loadPastRun, selectCluster, selectCandidate, reset,
} = useAuditStream()

const pastRuns = ref<RunListItem[]>([])
const selectedPastRunId = ref<string | null>(null)

const viewState = computed(() => {
  if (status.value === 'streaming') return 'streaming'
  if (status.value === 'completed' && selectedCandidateId.value) return 'reviewing'
  if (status.value === 'completed') return 'completed'
  return 'idle'
})

const selectedCluster = computed(() =>
  clusters.value.find(c => c.clusterId === selectedClusterId.value) ?? null
)

const selectedCandidate = computed(() =>
  candidates.value.find(c => c.candidate_id === selectedCandidateId.value) ?? null
)

async function fetchPastRuns(): Promise<void> {
  try {
    pastRuns.value = await $fetch<RunListItem[]>('/api/background-audits/runs')
  } catch { pastRuns.value = [] }
}

async function startNewAudit(): Promise<void> {
  selectedPastRunId.value = null
  await triggerRun(7)
}

function handleLoadPastRun(id: string): void {
  loadPastRun(id)
}

function handleSelectCandidate(candidateId: string): void {
  selectCandidate(candidateId)
}

function formatRunDate(dateString: string): string {
  return new Date(dateString).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function getRunPatternCount(run: RunListItem): number {
  const raw = run.counters?.candidates_generated ?? run.counters?.candidates ?? 0
  const value = Number(raw)
  return Number.isFinite(value) ? value : 0
}

const showHowItWorks = ref(false)

usePolling(fetchPastRuns, 5000)
</script>

<template>
  <div class="flex min-h-[calc(100vh-5rem)] flex-col">
    <!-- Header -->
    <div class="mb-4 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Fraud Pattern Discovery</h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ viewState === 'streaming' ? `Analyzing ${clusters.length} clusters...` :
             viewState === 'completed' || viewState === 'reviewing' ? `Found ${candidates.length} patterns` :
             'AI-powered pattern detection across transaction history' }}
        </p>
      </div>
      <div class="flex items-center gap-2">
        <button
          v-if="viewState === 'idle'"
          class="flex items-center gap-1.5 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          @click="startNewAudit"
        >
          <Icon icon="lucide:play" class="h-4 w-4" />
          Start New Audit
        </button>
        <button
          v-if="viewState !== 'idle' && viewState !== 'streaming'"
          class="flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          @click="reset()"
        >
          <Icon icon="lucide:refresh-cw" class="h-4 w-4" />
          New Audit
        </button>
        <div v-if="pastRuns.length > 0 && viewState === 'idle'" class="relative">
          <select
            v-model="selectedPastRunId"
            class="appearance-none rounded-lg border border-gray-300 bg-white pl-3 pr-8 py-2 text-sm text-gray-700"
            @change="selectedPastRunId && handleLoadPastRun(selectedPastRunId)"
          >
            <option :value="null">Past Runs</option>
            <option v-for="run in pastRuns" :key="run.run_id" :value="run.run_id">
              {{ formatRunDate(run.started_at) }} - {{ getRunPatternCount(run) }} patterns
            </option>
          </select>
          <Icon icon="lucide:chevron-down" class="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        </div>
      </div>
    </div>

    <!-- How it works -->
    <div class="mb-4 rounded-xl border border-blue-200 bg-blue-50/60">
      <button
        class="flex w-full items-center justify-between px-4 py-3 text-left"
        @click="showHowItWorks = !showHowItWorks"
      >
        <div class="flex items-center gap-2">
          <Icon icon="lucide:info" class="h-4 w-4 text-blue-600" />
          <span class="text-sm font-medium text-blue-800">How does this work?</span>
        </div>
        <Icon
          :icon="showHowItWorks ? 'lucide:chevron-up' : 'lucide:chevron-down'"
          class="h-4 w-4 text-blue-500"
        />
      </button>

      <div v-if="showHowItWorks" class="border-t border-blue-200 px-4 pb-4 pt-3">
        <p class="text-sm text-gray-700 leading-relaxed mb-3">
          The audit scans recent withdrawal activity for hidden fraud patterns that individual transactions might not reveal — things like coordinated withdrawal rings, shared device networks, or identity fraud clusters.
        </p>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div class="flex items-start gap-2.5">
            <div class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">1</div>
            <div>
              <p class="text-xs font-semibold text-gray-800">Collect Findings</p>
              <p class="text-xs text-gray-500">Gathers triage constellation analysis and investigator findings (financial, identity, cross-account) from recent withdrawals</p>
            </div>
          </div>
          <div class="flex items-start gap-2.5">
            <div class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">2</div>
            <div>
              <p class="text-xs font-semibold text-gray-800">Cluster Patterns</p>
              <p class="text-xs text-gray-500">Groups related signals using embeddings and clustering to find coordinated behavior across accounts</p>
            </div>
          </div>
          <div class="flex items-start gap-2.5">
            <div class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">3</div>
            <div>
              <p class="text-xs font-semibold text-gray-800">AI Investigation</p>
              <p class="text-xs text-gray-500">An AI agent runs SQL queries against the database and cross-references known fraud typologies for each cluster</p>
            </div>
          </div>
          <div class="flex items-start gap-2.5">
            <div class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">4</div>
            <div>
              <p class="text-xs font-semibold text-gray-800">Report Findings</p>
              <p class="text-xs text-gray-500">Deduplicates results and presents named fraud patterns with evidence and confidence scores</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Idle -->
    <div v-if="viewState === 'idle'" class="flex flex-1 items-center justify-center rounded-xl border border-gray-200 bg-white">
      <div class="max-w-md text-center">
        <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-50">
          <Icon icon="lucide:radar" class="h-8 w-8 text-primary-500" />
        </div>
        <h2 class="text-lg font-semibold text-gray-800">Ready to Discover Patterns</h2>
        <p class="mt-2 text-sm text-gray-500">
          Analyze transaction history, extract evidence, cluster patterns, and investigate with AI agents.
        </p>
        <button class="mt-6 inline-flex items-center gap-2 rounded-lg bg-primary-600 px-6 py-3 text-sm font-medium text-white hover:bg-primary-700" @click="startNewAudit">
          <Icon icon="lucide:play" class="h-5 w-5" />
          Start New Audit
        </button>
      </div>
    </div>

    <!-- Active State: Split View -->
    <template v-else>
      <AuditSplitView>
        <template #left>
          <div class="border-b border-gray-200 px-1 pb-3 mb-3">
            <h3 class="text-sm font-semibold text-gray-700">Pipeline Progress</h3>
          </div>
          <AuditPipelineTimeline
            :phases="phases"
            :clusters="clusters"
            :selected-cluster-id="selectedClusterId"
            @select-cluster="selectCluster"
          />
        </template>
        <template #right>
          <AuditContextViewer
            :selected-cluster="selectedCluster"
            :selected-candidate="selectedCandidate"
            :status="status"
          />
        </template>
      </AuditSplitView>

      <!-- Results Grid -->
      <div v-if="candidates.length > 0" class="mt-4">
        <AuditCandidateGrid
          :candidates="candidates"
          @select-candidate="handleSelectCandidate"
        />
      </div>
    </template>

    <!-- Error -->
    <div v-if="error" class="mt-4 flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      <Icon icon="lucide:alert-circle" class="h-5 w-5 shrink-0" />
      <span>{{ error }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { CandidateResult } from '~/utils/auditTypes'

interface Props {
  candidate: CandidateResult
}

const props = defineProps<Props>()

interface Section {
  title: string
  icon: string
  content: string | undefined
}

const sections = computed<Section[]>(() => {
  return [
    {
      title: 'Analyst Notes',
      icon: 'lucide:file-text',
      content: props.candidate.pattern_card.analyst_notes
    },
    {
      title: 'Limitations',
      icon: 'lucide:alert-triangle',
      content: props.candidate.pattern_card.limitations
    },
    {
      title: 'Uncertainty',
      icon: 'lucide:help-circle',
      content: props.candidate.pattern_card.uncertainty
    },
    {
      title: 'Clustering Notes',
      icon: 'lucide:git-branch',
      content: props.candidate.pattern_card.clustering_notes
    }
  ].filter((section) => section.content)
})
</script>

<template>
  <div class="space-y-4">
    <div v-if="sections.length === 0" class="text-center py-8">
      <Icon icon="lucide:brain-cog" class="mx-auto h-12 w-12 text-gray-300 mb-3" />
      <p class="text-sm text-gray-500">No agent reasoning notes available</p>
    </div>

    <div v-for="(section, idx) in sections" :key="idx" class="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div class="flex items-center gap-2 mb-3">
        <Icon :icon="section.icon" class="h-5 w-5 text-gray-500" />
        <h4 class="text-sm font-semibold text-gray-700">{{ section.title }}</h4>
      </div>

      <div class="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
        {{ section.content }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { formatDate } from '~/utils/formatters'

useHead({ title: 'Customers - Nexa' })

interface Customer {
  id: string
  name: string
  email: string
  country: string
  registration_date: string | null
  is_flagged: boolean
  flag_reason: string | null
}

const customers = ref<Customer[]>([])
const loading = ref(true)
const searchQuery = ref('')
const selectedFilter = ref<'all' | 'flagged' | 'clean'>('all')
const currentPage = ref(1)
const perPage = 10

async function fetchCustomers() {
  loading.value = true
  try {
    customers.value = await $fetch<Customer[]>('/api/customers')
  }
  catch {
    customers.value = []
  }
  finally {
    loading.value = false
  }
}

onMounted(fetchCustomers)

const filteredCustomers = computed(() => {
  let list = customers.value

  if (selectedFilter.value === 'flagged')
    list = list.filter(c => c.is_flagged)
  else if (selectedFilter.value === 'clean')
    list = list.filter(c => !c.is_flagged)

  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(c =>
      c.name.toLowerCase().includes(q)
      || c.email.toLowerCase().includes(q)
      || c.id.toLowerCase().includes(q)
      || c.country.toLowerCase().includes(q),
    )
  }

  return list
})

const totalPages = computed(() => Math.ceil(filteredCustomers.value.length / perPage) || 1)

const paginatedCustomers = computed(() => {
  const start = (currentPage.value - 1) * perPage
  return filteredCustomers.value.slice(start, start + perPage)
})

const filterCounts = computed(() => ({
  all: customers.value.length,
  flagged: customers.value.filter(c => c.is_flagged).length,
  clean: customers.value.filter(c => !c.is_flagged).length,
}))

const filterTabs: { key: 'all' | 'flagged' | 'clean', label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'flagged', label: 'Flagged' },
  { key: 'clean', label: 'Clean' },
]

function getInitials(name: string): string {
  return name.split(' ').map(n => n[0]).join('').toUpperCase()
}

const countryNames: Record<string, string> = {
  MY: 'Malaysia', SG: 'Singapore', ID: 'Indonesia', TH: 'Thailand',
  VN: 'Vietnam', PH: 'Philippines', GB: 'United Kingdom', US: 'United States',
  DE: 'Germany', FR: 'France', JP: 'Japan', AU: 'Australia',
  IN: 'India', BR: 'Brazil', NG: 'Nigeria', AE: 'UAE',
}

function getCountryLabel(code: string): string {
  return countryNames[code] || code
}

const showDrawer = ref(false)
const selectedCustomerId = ref('')

function openWeightsDrawer(customer: Customer) {
  selectedCustomerId.value = customer.id
  showDrawer.value = true
}
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">
          Customers
        </h1>
        <p class="text-sm text-gray-500 mt-1">
          View and manage all registered customers
        </p>
      </div>
    </div>

    <!-- Filter Tabs -->
    <div class="flex items-center gap-1 bg-gray-100 p-1 rounded-lg w-fit">
      <button
        v-for="tab in filterTabs"
        :key="tab.key"
        class="px-4 py-2 text-sm font-medium rounded-md transition-all"
        :class="selectedFilter === tab.key
          ? 'bg-white text-gray-900 shadow-sm'
          : 'text-gray-600 hover:text-gray-800'"
        @click="selectedFilter = tab.key; currentPage = 1"
      >
        {{ tab.label }}
        <span
          class="ml-1.5 px-1.5 py-0.5 text-xs rounded-full"
          :class="selectedFilter === tab.key ? 'bg-gray-200 text-gray-700' : 'bg-gray-200/70 text-gray-500'"
        >
          {{ filterCounts[tab.key] }}
        </span>
      </button>
    </div>

    <!-- Search -->
    <div class="flex flex-wrap items-center gap-4">
      <div class="relative flex-1 min-w-[280px] max-w-md">
        <Icon icon="lucide:search" class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by name, email, ID, or country..."
          class="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          @input="currentPage = 1"
        >
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="bg-white rounded-xl border border-gray-200 px-4 py-12 text-center">
      <Icon icon="lucide:loader-2" class="w-8 h-8 text-gray-400 mx-auto mb-3 animate-spin" />
      <p class="text-gray-500 text-sm">
        Loading customers...
      </p>
    </div>

    <!-- Customers Table -->
    <div v-else class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="bg-gray-50 border-b border-gray-200">
              <th class="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Customer
              </th>
              <th class="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                ID
              </th>
              <th class="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Country
              </th>
              <th class="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Registered
              </th>
              <th class="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th class="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Weights
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr
              v-for="customer in paginatedCustomers"
              :key="customer.id"
              class="hover:bg-gray-50/50 transition-colors cursor-pointer"
              @click="openWeightsDrawer(customer)"
            >
              <!-- Customer Name + Email -->
              <td class="px-4 py-3.5">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 bg-primary-50 rounded-full flex items-center justify-center shrink-0">
                    <span class="text-primary-700 font-medium text-xs">
                      {{ getInitials(customer.name) }}
                    </span>
                  </div>
                  <div class="min-w-0">
                    <p class="text-sm font-medium text-gray-900 truncate">
                      {{ customer.name }}
                    </p>
                    <p class="text-xs text-gray-500 truncate">
                      {{ customer.email }}
                    </p>
                  </div>
                </div>
              </td>

              <!-- External ID -->
              <td class="px-4 py-3.5">
                <span class="text-sm text-gray-600 font-mono">{{ customer.id }}</span>
              </td>

              <!-- Country -->
              <td class="px-4 py-3.5">
                <span class="text-sm text-gray-600">{{ getCountryLabel(customer.country) }}</span>
              </td>

              <!-- Registration Date -->
              <td class="px-4 py-3.5">
                <span class="text-sm text-gray-500">
                  {{ customer.registration_date ? formatDate(customer.registration_date, 'MMM dd, yyyy') : '—' }}
                </span>
              </td>

              <!-- Flagged Status -->
              <td class="px-4 py-3.5">
                <div class="flex items-center gap-2">
                  <span
                    class="inline-flex px-2.5 py-1 text-xs font-medium rounded-full"
                    :class="customer.is_flagged
                      ? 'bg-red-100 text-red-700'
                      : 'bg-green-100 text-green-700'"
                  >
                    {{ customer.is_flagged ? 'Flagged' : 'Clean' }}
                  </span>
                  <span
                    v-if="customer.is_flagged && customer.flag_reason"
                    class="text-xs text-gray-500 truncate max-w-[200px]"
                    :title="customer.flag_reason"
                  >
                    {{ customer.flag_reason }}
                  </span>
                </div>
              </td>

              <!-- Weights Action -->
              <td class="px-4 py-3.5 text-right" @click.stop>
                <button
                  class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-primary-700 bg-primary-50 border border-primary-200 rounded-lg hover:bg-primary-100 transition-colors"
                  @click="openWeightsDrawer(customer)"
                >
                  <Icon icon="lucide:bar-chart-3" class="w-3.5 h-3.5" />
                  View
                </button>
              </td>
            </tr>

            <!-- Empty State -->
            <tr v-if="paginatedCustomers.length === 0">
              <td colspan="6" class="px-4 py-12 text-center">
                <Icon icon="lucide:users" class="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p class="text-gray-500 text-sm">
                  No customers found matching your filters
                </p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
        <p class="text-sm text-gray-600">
          Showing {{ paginatedCustomers.length }} of {{ filteredCustomers.length }} customers
        </p>
        <div class="flex items-center gap-2">
          <button
            class="px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="currentPage <= 1"
            @click="currentPage--"
          >
            Previous
          </button>
          <span class="text-sm text-gray-600 px-2">
            Page {{ currentPage }} of {{ totalPages }}
          </span>
          <button
            class="px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="currentPage >= totalPages"
            @click="currentPage++"
          >
            Next
          </button>
        </div>
      </div>
    </div>
    <!-- Scoring Factors Drawer -->
    <ScoringFactorsDrawer
      :visible="showDrawer"
      :customer-id="selectedCustomerId"
      :risk-score="0"
      decision=""
      @close="showDrawer = false; selectedCustomerId = ''"
    />
  </div>
</template>

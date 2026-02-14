import { ref } from 'vue'

const appliedActions = ref<Set<string>>(new Set())

export function useDriftActions() {
  async function pinIndicator(customerId: string, indicatorName: string): Promise<void> {
    await $fetch(`/api/customers/${customerId}/weights/pin`, {
      method: 'POST',
      body: { indicator_name: indicatorName, is_pinned: true },
    })
    appliedActions.value.add(`pin:${customerId}:${indicatorName}`)
  }

  async function resetCustomer(customerId: string): Promise<void> {
    await $fetch(`/api/customers/${customerId}/weights/reset`, {
      method: 'POST',
      body: { reason: 'Weight drift outlier reset', updated_by: 'audit_drift' },
    })
    appliedActions.value.add(`reset:${customerId}`)
  }

  async function downloadPdf(runId: string): Promise<void> {
    const response = await $fetch<Blob>(
      `/api/background-audits/runs/${runId}/drift-pdf`,
      { responseType: 'blob' },
    )
    const url = URL.createObjectURL(response)
    const a = document.createElement('a')
    a.href = url
    a.download = `drift-report-${runId}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  }

  function isApplied(key: string): boolean {
    return appliedActions.value.has(key)
  }

  function dismissAction(key: string): void {
    appliedActions.value.add(key)
  }

  return { pinIndicator, resetCustomer, downloadPdf, isApplied, dismissAction, appliedActions }
}

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const query = getQuery(event)
  const days = query.days || 7
  return $fetch(`/api/dashboard/decision-trend?days=${days}`, {
    baseURL: config.apiBase,
    headers: getHeaders(event) as HeadersInit,
  })
})

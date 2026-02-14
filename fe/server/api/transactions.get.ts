export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const query = getQuery(event)
  return $fetch('/api/transactions', {
    baseURL: config.apiBase,
    query,
    headers: getHeaders(event) as HeadersInit,
  })
})

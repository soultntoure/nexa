export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  return $fetch('/api/dashboard/stats', {
    baseURL: config.apiBase,
    headers: getHeaders(event) as HeadersInit,
  })
})

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  return $fetch('/api/settings', {
    baseURL: config.apiBase,
    headers: getHeaders(event) as HeadersInit,
  })
})

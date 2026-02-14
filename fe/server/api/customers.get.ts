export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  return $fetch('/api/customers', {
    baseURL: config.apiBase,
    headers: getHeaders(event) as HeadersInit,
  })
})

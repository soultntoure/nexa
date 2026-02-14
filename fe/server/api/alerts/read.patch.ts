export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const body = await readBody(event)
  return $fetch('/api/alerts/read', {
    method: 'PATCH',
    baseURL: config.apiBase,
    body,
    headers: getHeaders(event) as HeadersInit,
  })
})

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const body = await readBody(event)
  return $fetch('/api/settings', {
    baseURL: config.apiBase,
    method: 'POST',
    body,
    headers: getHeaders(event) as HeadersInit,
  })
})

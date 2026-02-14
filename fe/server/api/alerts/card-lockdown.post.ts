export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const body = await readBody(event)
  return $fetch('/api/alerts/card-lockdown', {
    method: 'POST',
    baseURL: config.apiBase,
    body,
  })
})

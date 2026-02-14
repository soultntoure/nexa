export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const body = await readBody(event)
  return $fetch('/api/payout/decision', {
    method: 'POST',
    baseURL: config.apiBase,
    body,
  })
})

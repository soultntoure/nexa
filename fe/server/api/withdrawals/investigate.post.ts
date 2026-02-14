export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const body = await readBody(event)
  return $fetch('/api/withdrawals/investigate', {
    method: 'POST',
    baseURL: config.apiBase,
    body,
  })
})

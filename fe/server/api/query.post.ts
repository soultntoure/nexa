export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const body = await readBody(event)
  return $fetch('/api/query', {
    method: 'POST',
    baseURL: config.apiBase,
    body,
  })
})

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const id = getRouterParam(event, 'id')
  const query = getQuery(event)

  return $fetch(`/api/payout/evaluate/${id}`, {
    baseURL: config.apiBase,
    query,
    headers: getHeaders(event) as HeadersInit,
  })
})

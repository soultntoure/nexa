export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const id = getRouterParam(event, 'id')
  return $fetch(`/api/payouts/${id}`, {
    baseURL: config.apiBase,
    headers: getHeaders(event) as HeadersInit,
  })
})

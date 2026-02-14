export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const externalId = getRouterParam(event, 'externalId')
  return $fetch(`/api/customers/${externalId}/weights`, {
    baseURL: config.apiBase,
    headers: getHeaders(event) as HeadersInit,
  })
})

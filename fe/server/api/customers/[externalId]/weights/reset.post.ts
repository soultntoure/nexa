export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const externalId = getRouterParam(event, 'externalId')
  const body = await readBody(event)
  return $fetch(`/api/customers/${externalId}/weights/reset`, {
    method: 'POST',
    baseURL: config.apiBase,
    body,
  })
})

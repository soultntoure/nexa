import type { H3Event } from 'h3'

export default defineEventHandler(async (event: H3Event): Promise<unknown> => {
  const config = useRuntimeConfig()
  const body = await readBody(event)
  return $fetch('/api/settings', {
    baseURL: config.apiBase,
    method: 'POST',
    body,
  })
})

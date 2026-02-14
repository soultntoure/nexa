export default defineEventHandler(async () => {
  const config = useRuntimeConfig()
  return $fetch('/api/admins', {
    baseURL: config.apiBase,
  })
})

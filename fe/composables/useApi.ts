import type { UseFetchOptions } from 'nuxt/app'

export function useApi<T>(
  endpoint: string,
  options: UseFetchOptions<T> = {},
) {
  return useFetch<T>(`/api${endpoint}`, {
    ...options,
  })
}

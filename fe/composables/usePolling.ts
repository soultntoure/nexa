export function usePolling(callback: () => void | Promise<void>, intervalMs: number = 10000) {
  let timer: ReturnType<typeof setInterval> | null = null

  function start() {
    callback()
    timer = setInterval(() => {
      if (document.visibilityState === 'visible') {
        callback()
      }
    }, intervalMs)
  }

  function stop() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  if (import.meta.client) {
    start()
  }

  onUnmounted(stop)

  return { start, stop }
}

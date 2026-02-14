/**
 * Queues incoming text chunks and renders them character-by-character
 * with a small delay for a smooth typewriter streaming effect.
 */
export function useTypewriter(delay = 12) {
  const displayed = ref('')
  const queue = ref('')
  let timer: ReturnType<typeof setInterval> | null = null

  function push(text: string) {
    queue.value += text
    if (!timer) startDrain()
  }

  function startDrain() {
    timer = setInterval(() => {
      if (queue.value.length === 0) {
        if (timer) clearInterval(timer)
        timer = null
        return
      }
      // Drain in small bursts (2-4 chars) to keep up with fast streams
      const burst = Math.min(queue.value.length, 3)
      displayed.value += queue.value.slice(0, burst)
      queue.value = queue.value.slice(burst)
    }, delay)
  }

  /** Flush all remaining text immediately (on stream end). */
  function flush() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    displayed.value += queue.value
    queue.value = ''
  }

  function reset() {
    flush()
    displayed.value = ''
    queue.value = ''
  }

  const isAnimating = computed(() => queue.value.length > 0)

  onUnmounted(() => {
    if (timer) clearInterval(timer)
  })

  return { displayed, push, flush, reset, isAnimating }
}

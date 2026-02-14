export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const body = await readBody(event)

  const response = await fetch(`${config.apiBase}/api/query/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok || !response.body) {
    throw createError({ statusCode: response.status, statusMessage: 'SSE proxy failed' })
  }

  setResponseHeaders(event, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache, no-transform',
    'Connection': 'keep-alive',
    'X-Accel-Buffering': 'no',
  })

  // Pipe the upstream ReadableStream directly to the response
  const reader = response.body.getReader()
  const res = event.node.res

  // Send headers immediately to establish SSE connection
  res.flushHeaders()

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      res.write(value)
      // Force flush each SSE chunk immediately
      if (typeof (res as any).flush === 'function') {
        ;(res as any).flush()
      }
    }
  } finally {
    res.end()
  }
})

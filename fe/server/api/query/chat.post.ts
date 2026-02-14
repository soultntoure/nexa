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
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
  })

  // Pipe the upstream ReadableStream directly to the response
  const reader = response.body.getReader()
  const writable = event.node.res

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      writable.write(value)
    }
  } finally {
    writable.end()
  }
})

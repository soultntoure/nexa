import type { H3Event } from 'h3'

function getForwardHeaders(event: H3Event): HeadersInit {
  const headers = { ...getHeaders(event) } as Record<string, string | string[]>
  delete headers['content-length']
  delete headers['host']
  delete headers['connection']
  return headers as HeadersInit
}

export default defineEventHandler(async (event: H3Event): Promise<unknown> => {
  const config = useRuntimeConfig()
  const path = event.context.params?.path || ''
  const fullPath = Array.isArray(path) ? path.join('/') : path

  const isStreamEndpoint = fullPath.includes('/stream')

  if (isStreamEndpoint) {
    const response = await fetch(`${config.apiBase}/api/background-audits/${fullPath}`, {
      method: getMethod(event),
      headers: getForwardHeaders(event),
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

    const reader = response.body.getReader()
    const res = event.node.res

    res.flushHeaders()

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        res.write(value)
        if (typeof (res as any).flush === 'function') {
          (res as any).flush()
        }
      }
    } finally {
      res.end()
    }
  } else {
    const method = getMethod(event)
    const body = method !== 'GET' && method !== 'HEAD' ? await readBody(event).catch(() => null) : null
    const query = getQuery(event)

    return $fetch(`/api/background-audits/${fullPath}`, {
      method,
      baseURL: config.apiBase,
      body,
      query,
      headers: getForwardHeaders(event),
    })
  }
})

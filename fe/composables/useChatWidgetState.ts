import type { QueryMessage } from '~/components/query/QueryMessageBubble.vue'
import type { WithdrawalDiscussionContext } from '~/composables/useWithdrawalDiscussion'

export function useChatWidgetState() {
  const isOpen = useState<boolean>('chat-widget-open', () => false)
  const messages = useState<QueryMessage[]>('chat-widget-messages', () => [])
  const sessionId = useState<string>('chat-widget-session', () => generateId())
  const widgetContext = useState<WithdrawalDiscussionContext | null>('chat-widget-context', () => null)

  function toggle() {
    isOpen.value = !isOpen.value
  }

  function open() {
    isOpen.value = true
  }

  function close() {
    isOpen.value = false
  }

  function clearChat() {
    messages.value = []
    sessionId.value = generateId()
    widgetContext.value = null
  }

  function openWithContext(ctx: WithdrawalDiscussionContext) {
    // Fresh session for the new withdrawal context
    messages.value = []
    sessionId.value = generateId()
    widgetContext.value = ctx
    isOpen.value = true
  }

  function dismissContext() {
    widgetContext.value = null
  }

  function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2)
  }

  return { isOpen, messages, sessionId, widgetContext, toggle, open, close, clearChat, openWithContext, dismissContext, generateId }
}

import { format, parseISO } from 'date-fns'

export function formatCurrency(amount: number, currency = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

export function formatDate(date: string | Date, pattern = 'MMM dd, yyyy HH:mm'): string {
  const d = typeof date === 'string' ? parseISO(date) : date
  return format(d, pattern)
}

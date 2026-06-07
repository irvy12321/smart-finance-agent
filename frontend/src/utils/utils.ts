import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}

export function formatDuration(ms: number): string {
  if (ms >= 1000) {
    return (ms / 1000).toFixed(1) + 's'
  }
  return ms.toFixed(0) + 'ms'
}

export function formatPercentage(value: number): string {
  return (value * 100).toFixed(1) + '%'
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '...'
}

export function getStatusColor(status: string): string {
  switch (status) {
    case 'completed':
    case 'success':
      return 'text-green-500'
    case 'running':
      return 'text-blue-500'
    case 'error':
    case 'failed':
      return 'text-red-500'
    case 'pending':
      return 'text-yellow-500'
    default:
      return 'text-gray-500'
  }
}

export function getStatusBgColor(status: string): string {
  switch (status) {
    case 'completed':
    case 'success':
      return 'bg-green-500/10'
    case 'running':
      return 'bg-blue-500/10'
    case 'error':
    case 'failed':
      return 'bg-red-500/10'
    case 'pending':
      return 'bg-yellow-500/10'
    default:
      return 'bg-gray-500/10'
  }
}

export function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateString
  }
}

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout>
  return (...args: Parameters<T>) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}
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

export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout>
  return (...args: Parameters<T>) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

/**
 * Clean AI-generated markdown formatting from text.
 * Removes **bold**, ## headings, etc. while preserving actual content.
 * Converts * list items to bullet points •
 */
export function cleanAIText(text: string): string {
  if (!text) return ''

  return text
    // Remove markdown bold **text** → text
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    // Remove markdown headings ## text → text
    .replace(/^#{1,6}\s+/gm, '')
    // Remove markdown italic *text* → text (but not multiplication like 2*3)
    .replace(/(?<!\w)\*([^*\n]+)\*(?!\w)/g, '$1')
    // Convert * and - list items to bullet points
    .replace(/^(\s*)[*-]\s+/gm, '$1• ')
    // Remove markdown code blocks ```...```
    .replace(/```[\s\S]*?```/g, (match) => match.replace(/```\w*\n?/g, '').replace(/```/g, ''))
    // Remove inline code `text`
    .replace(/`([^`]+)`/g, '$1')
    // Remove markdown links [text](url) → text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    // Clean up extra blank lines
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

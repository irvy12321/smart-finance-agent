import { useState, useEffect, useRef, useCallback } from 'react'
import { Bot, User, Loader2, Copy, CheckCircle, ThumbsUp, ThumbsDown } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'

interface StreamingMessageProps {
  content: string
  isStreaming?: boolean
  role: 'user' | 'assistant'
  timestamp?: string
  onCopy?: (content: string) => void
  onFeedback?: (positive: boolean) => void
}

export function StreamingMessage({
  content,
  isStreaming = false,
  role,
  timestamp,
  onCopy,
  onFeedback,
}: StreamingMessageProps) {
  const [displayedContent, setDisplayedContent] = useState('')
  const [isComplete, setIsComplete] = useState(false)
  const [copied, setCopied] = useState(false)
  const [feedback, setFeedback] = useState<boolean | null>(null)
  const contentRef = useRef(content)
  const indexRef = useRef(0)

  useEffect(() => {
    contentRef.current = content
    if (!isStreaming) {
      setDisplayedContent(content)
      setIsComplete(true)
      return
    }

    setDisplayedContent('')
    indexRef.current = 0
    setIsComplete(false)

    const interval = setInterval(() => {
      if (indexRef.current < contentRef.current.length) {
        const nextIndex = Math.min(indexRef.current + 3, contentRef.current.length)
        setDisplayedContent(contentRef.current.slice(0, nextIndex))
        indexRef.current = nextIndex
      } else {
        setIsComplete(true)
        clearInterval(interval)
      }
    }, 15)

    return () => clearInterval(interval)
  }, [content, isStreaming])

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(content)
    setCopied(true)
    onCopy?.(content)
    setTimeout(() => setCopied(false), 2000)
  }, [content, onCopy])

  const handleFeedback = useCallback((positive: boolean) => {
    setFeedback(positive)
    onFeedback?.(positive)
  }, [onFeedback])

  const markdownComponents = {
    p: ({ children }: any) => <p className="text-sm leading-relaxed mb-2 last:mb-0">{children}</p>,
    ul: ({ children }: any) => <ul className="list-disc list-inside text-sm mb-2 space-y-1">{children}</ul>,
    ol: ({ children }: any) => <ol className="list-decimal list-inside text-sm mb-2 space-y-1">{children}</ol>,
    li: ({ children }: any) => <li>{children}</li>,
    code: ({ children, className }: any) => {
      const isInline = !className
      return isInline ? (
        <code className="bg-dark-bg px-1.5 py-0.5 rounded text-xs font-mono">{children}</code>
      ) : (
        <pre className="bg-dark-bg p-3 rounded-lg overflow-x-auto mb-2">
          <code className="text-xs font-mono">{children}</code>
        </pre>
      )
    },
    strong: ({ children }: any) => <strong className="font-semibold">{children}</strong>,
    em: ({ children }: any) => <em className="italic">{children}</em>,
    h1: ({ children }: any) => <h1 className="text-lg font-bold mb-2">{children}</h1>,
    h2: ({ children }: any) => <h2 className="text-base font-semibold mb-2">{children}</h2>,
    h3: ({ children }: any) => <h3 className="text-sm font-semibold mb-1">{children}</h3>,
  }

  return (
    <div className={`flex gap-3 ${role === 'user' ? 'justify-end' : 'justify-start'}`}>
      {role === 'assistant' && (
        <div className="w-8 h-8 bg-primary-500/10 rounded-lg flex items-center justify-center flex-shrink-0">
          <Bot className="w-4 h-4 text-primary-500" />
        </div>
      )}

      <div className={`max-w-[80%] ${role === 'user' ? 'order-first' : ''}`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            role === 'user'
              ? 'bg-primary-500 text-white'
              : 'bg-dark-card border border-dark-border'
          }`}
        >
          {role === 'assistant' ? (
            <div className="text-primary-200">
              <ReactMarkdown rehypePlugins={[rehypeSanitize]} components={markdownComponents}>
                {displayedContent}
              </ReactMarkdown>
              {isStreaming && !isComplete && (
                <span className="inline-block w-2 h-4 bg-primary-500 ml-1 animate-pulse" />
              )}
            </div>
          ) : (
            <p className="text-sm whitespace-pre-wrap">{displayedContent}</p>
          )}
        </div>

        {/* Actions for assistant messages */}
        {role === 'assistant' && isComplete && (
          <div className="flex items-center gap-2 mt-1.5 ml-1">
            {timestamp && (
              <span className="text-xs text-primary-500">
                {new Date(timestamp).toLocaleTimeString()}
              </span>
            )}
            <div className="flex items-center gap-1">
              <button
                onClick={handleCopy}
                className="p-1 text-primary-400 hover:text-primary-200 transition-colors rounded"
                title="Copy"
              >
                {copied ? (
                  <CheckCircle className="w-3.5 h-3.5 text-green-500" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
              </button>
              <button
                onClick={() => handleFeedback(true)}
                className={`p-1 transition-colors rounded ${
                  feedback === true ? 'text-green-500' : 'text-primary-400 hover:text-primary-200'
                }`}
                title="Good response"
              >
                <ThumbsUp className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => handleFeedback(false)}
                className={`p-1 transition-colors rounded ${
                  feedback === false ? 'text-red-500' : 'text-primary-400 hover:text-primary-200'
                }`}
                title="Bad response"
              >
                <ThumbsDown className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* User message timestamp */}
        {role === 'user' && timestamp && (
          <div className="text-xs text-primary-500 mt-1 mr-1 text-right">
            {new Date(timestamp).toLocaleTimeString()}
          </div>
        )}
      </div>

      {role === 'user' && (
        <div className="w-8 h-8 bg-blue-500/10 rounded-lg flex items-center justify-center flex-shrink-0">
          <User className="w-4 h-4 text-blue-500" />
        </div>
      )}
    </div>
  )
}

export function StreamingIndicator() {
  return (
    <div className="flex gap-3 justify-start">
      <div className="w-8 h-8 bg-primary-500/10 rounded-lg flex items-center justify-center flex-shrink-0">
        <Bot className="w-4 h-4 text-primary-500" />
      </div>
      <div className="bg-dark-card border border-dark-border rounded-2xl px-4 py-3">
        <div className="flex items-center gap-2">
          <Loader2 className="w-4 h-4 text-primary-400 animate-spin" />
          <span className="text-sm text-primary-400">Thinking...</span>
        </div>
      </div>
    </div>
  )
}

export default StreamingMessage

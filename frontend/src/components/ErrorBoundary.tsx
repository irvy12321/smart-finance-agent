import { Component, ErrorInfo, ReactNode } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'
import * as Sentry from '@sentry/react'
import { withTranslation, WithTranslation } from 'react-i18next'

interface Props extends WithTranslation {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
  eventId: string | null
}

class ErrorBoundaryClass extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null, eventId: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, eventId: null }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)

    const eventId = Sentry.captureException(error, {
      contexts: {
        react: {
          componentStack: errorInfo.componentStack,
        },
      },
    })

    this.setState({ eventId })
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, eventId: null })
  }

  handleReportFeedback = () => {
    if (this.state.eventId) {
      Sentry.showReportDialog({ eventId: this.state.eventId })
    }
  }

  render() {
    const { t } = this.props

    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="flex items-center justify-center h-full p-8">
          <div className="max-w-md w-full bg-dark-card border border-red-500/30 rounded-xl p-6 text-center">
            <div className="w-16 h-16 bg-red-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="w-8 h-8 text-red-500" />
            </div>
            <h2 className="text-xl font-bold text-primary-50 mb-2">
              {t('error.somethingWentWrong')}
            </h2>
            <p className="text-sm text-primary-400 mb-4">
              {this.state.error?.message || t('error.unexpectedError')}
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                onClick={this.handleReset}
                className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                {t('error.tryAgain')}
              </button>
              {this.state.eventId && (
                <button
                  onClick={this.handleReportFeedback}
                  className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-dark-bg hover:bg-dark-border text-primary-300 rounded-lg transition-colors"
                >
                  {t('error.reportFeedback')}
                </button>
              )}
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

const ErrorBoundary = withTranslation()(ErrorBoundaryClass)

export default ErrorBoundary

import * as Sentry from '@sentry/react'

const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN
const ENVIRONMENT = import.meta.env.MODE || 'development'
const IS_PRODUCTION = import.meta.env.PROD

export function initSentry() {
  if (!SENTRY_DSN) {
    console.warn('Sentry DSN not configured. Set VITE_SENTRY_DSN in .env')
    return
  }

  Sentry.init({
    dsn: SENTRY_DSN,
    environment: ENVIRONMENT,
    enabled: IS_PRODUCTION,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
    tracesSampleRate: IS_PRODUCTION ? 0.1 : 1.0,
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: IS_PRODUCTION ? 1.0 : 0,
    beforeSend(event) {
      if (event.exception) {
        const error = event.exception.values?.[0]
        if (error?.type === 'ChunkLoadError' || error?.value?.includes('Loading chunk')) {
          return null
        }
      }
      return event
    },
  })
}

export { Sentry }

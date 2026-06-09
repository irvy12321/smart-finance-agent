import React from 'react'
import ReactDOM from 'react-dom/client'
import * as Sentry from '@sentry/react'
import App from './App.tsx'
import { initSentry } from './services/sentry'
import './i18n'
import './index.css'

initSentry()

const root = document.getElementById('root')!

const AppWithSentry = Sentry.withErrorBoundary(App, {
  fallback: <div>Something went wrong</div>,
  showDialog: true,
})

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <AppWithSentry />
  </React.StrictMode>,
)

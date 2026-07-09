# Sentry Error Monitoring Setup

This document explains how to set up and configure Sentry error monitoring for Smart Finance Agent.

## Overview

Sentry is integrated into both frontend and backend:

- **Frontend**: Captures React errors via ErrorBoundary, browser exceptions, and performance traces
- **Backend**: Captures FastAPI exceptions, request errors, and logs

## Configuration

### 1. Create Sentry Account

1. Go to [sentry.io](https://sentry.io/) and create an account
2. Create a new project for "React" (frontend) and "Python" (backend)
3. Copy the DSN for each project

### 2. Frontend Configuration

Create `frontend/.env` file:

```env
VITE_SENTRY_DSN=https://your-dsn@sentry.io/project-id
VITE_APP_ENV=development
```

### 3. Backend Configuration

Add to `backend/.env` file:

```env
SENTRY_DSN=https://your-dsn@sentry.io/project-id
ENVIRONMENT=development
```

## Features

### Frontend

- **ErrorBoundary Integration**: React component errors are automatically captured
- **Browser Tracing**: Performance monitoring for page loads and navigation
- **Session Replay**: Records user sessions when errors occur (configurable)
- **Source Maps**: Upload source maps for better stack traces in production

### Backend

- **FastAPI Integration**: Automatic capture of unhandled exceptions
- **Logging Integration**: ERROR level logs are sent to Sentry
- **Request Context**: HTTP request details are attached to errors
- **Sensitive Data Filtering**: Authorization/cookie/API-key headers, sensitive query tokens, and password/token fields are automatically filtered

## Testing Sentry Integration

### Frontend

1. Add a test button that throws an error:

```tsx
<button onClick={() => { throw new Error('Test Sentry Error') }}>
  Test Sentry
</button>
```

2. Check Sentry dashboard for the captured error

### Backend

1. Call the debug endpoint:

```bash
curl http://localhost:8000/sentry-debug
```

2. Check Sentry dashboard for the captured exception

## Production Deployment

### Environment Variables

Set these in your production environment:

```env
# Frontend (build-time)
VITE_SENTRY_DSN=https://your-dsn@sentry.io/project-id
VITE_APP_ENV=production

# Backend (runtime)
SENTRY_DSN=https://your-dsn@sentry.io/project-id
ENVIRONMENT=production
```

### Source Map Upload (Optional)

To upload source maps for better stack traces:

1. Install Sentry CLI: `npm install -g @sentry/cli`
2. Configure `.sentryclirc`:

```ini
[defaults]
org=your-org
project=your-project

[auth]
token=your-auth-token
```

3. Add to build script in `package.json`:

```json
{
  "scripts": {
    "build": "tsc && vite build && sentry-cli sourcemaps upload ./dist"
  }
}
```

## Monitoring Dashboard

After setup, you can monitor:

- **Issues**: Unhandled exceptions and errors
- **Performance**: Page load times, API response times
- **Replays**: User sessions when errors occurred
- **Alerts**: Configure notifications for critical errors

## Best Practices

1. **Don't send PII**: Sentry is configured to filter sensitive data
2. **Use environments**: Separate development/staging/production in Sentry
3. **Set up alerts**: Configure Slack/email notifications for critical errors
4. **Review regularly**: Check Sentry dashboard for recurring issues
5. **Add context**: Use `Sentry.setContext()` to add useful debugging information

## Troubleshooting

### Sentry not capturing errors

1. Check if DSN is configured correctly
2. Verify `enabled` is `true` (only in production by default)
3. Check browser console for Sentry initialization logs

### Missing stack traces

1. Ensure source maps are generated in production builds
2. Upload source maps to Sentry for better debugging

### Too many events

1. Adjust `tracesSampleRate` in configuration
2. Use `beforeSend` to filter unnecessary events
3. Set up rate limiting in Sentry project settings

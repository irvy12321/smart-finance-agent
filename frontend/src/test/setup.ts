import { vi } from 'vitest'
import React from 'react'
import '@testing-library/jest-dom'
import en from '../i18n/locales/en.json'

// Helper to get nested translation value
function getTranslation(key: string): string {
  const keys = key.split('.')
  let value: unknown = en
  for (const k of keys) {
    if (value && typeof value === 'object' && k in value) {
      value = (value as Record<string, unknown>)[k]
    } else {
      return key
    }
  }
  return typeof value === 'string' ? value : key
}

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => getTranslation(key),
    i18n: {
      changeLanguage: vi.fn(),
      language: 'en',
    },
  }),
  Trans: ({ children }: { children: React.ReactNode }) => children,
  withTranslation: () => (Component: React.ComponentType) => {
    const WrappedComponent = (props: Record<string, unknown>) => {
      return React.createElement(Component as React.ComponentType<Record<string, unknown>>, { ...props, t: (key: string) => getTranslation(key) })
    }
    WrappedComponent.displayName = `withTranslation(${Component.displayName || Component.name || 'Component'})`
    return WrappedComponent
  },
  initReactI18next: {
    type: '3rdParty',
    init: vi.fn(),
  },
}))

// Mock IntersectionObserver
class MockIntersectionObserver {
  observe = vi.fn()
  disconnect = vi.fn()
  unobserve = vi.fn()
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  value: MockIntersectionObserver,
})

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock scrollTo
window.scrollTo = vi.fn()

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f0f5',
          100: '#e0e0e0',
          200: '#c0c0d0',
          300: '#a0a0b0',
          400: '#8888a0',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#312e81',
          800: '#1e1e2e',
          900: '#0a0a0f',
        },
        dark: {
          bg: '#0a0a0f',
          card: '#1a1a2e',
          sub: '#12121a',
          border: '#2a2a3e',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['SF Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
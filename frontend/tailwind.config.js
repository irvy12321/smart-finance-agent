/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // `primary` is used both for neutral text (50-400) and the brand accent (500-700).
        // Neutralised greys + a single calm-blue accent — no indigo/violet.
        primary: {
          50: '#e9eaec',
          100: '#d7dade',
          200: '#b9bdc3',
          300: '#9aa0a8',
          400: '#7c828b',
          500: '#5b9dff',
          600: '#4f8fee',
          700: '#3f73c0',
          800: '#1a1c1f',
          900: '#0c0d0e',
        },
        dark: {
          bg: '#0c0d0e',
          card: '#141517',
          sub: '#101113',
          hover: '#1a1c1f',
          border: '#26282c',
        },
        // Data semantics — gains/losses carry the colour, not the chrome.
        up: '#37d39b',
        down: '#ff5f6b',
        accent: '#5b9dff',
      },
      fontFamily: {
        sans: ['Geist', 'Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['Geist Mono', 'SF Mono', 'Fira Code', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}

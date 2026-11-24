/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: '#F7F7F5',
        hairline: '#E2E2DF',
        'carbon-ink': '#141413',
        'slate-label': '#6E6E6A',
        'subtle-surface': '#EEEEEC',
        'card-bg': '#FFFFFF',
        'burnt-orange': '#FF4F00',
        'burnt-orange-subtle': '#FFF2EB',
        'emerald-booked': '#15803D',
        'emerald-subtle': '#ECFDF5',
        'amber-warm': '#D97706',
        'amber-subtle': '#FFFBEB'
      },
      fontFamily: {
        sans: ['"Inter"', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace']
      },
      boxShadow: {
        'tactile': '0 1px 2px rgba(0, 0, 0, 0.04), 0 0 0 1px rgba(0, 0, 0, 0.06)',
        'tactile-hover': '0 2px 4px rgba(0, 0, 0, 0.06), 0 0 0 1px rgba(0, 0, 0, 0.10)',
        'tactile-pressed': 'inset 0 1px 2px rgba(0, 0, 0, 0.1)',
        'drawer': '-8px 0 32px rgba(20, 20, 19, 0.08), 0 0 0 1px #E2E2DF'
      }
    },
  },
  plugins: [],
}
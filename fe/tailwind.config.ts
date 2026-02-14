import type { Config } from 'tailwindcss'

export default {
  content: [
    './components/**/*.{vue,ts}',
    './layouts/**/*.vue',
    './pages/**/*.vue',
    './composables/**/*.ts',
    './plugins/**/*.ts',
    './app.vue',
  ],
  theme: {
    extend: {
      borderRadius: {
        sm: '0.375rem',
        DEFAULT: '0.375rem',
        md: '0.375rem',
        lg: '0.375rem',
        xl: '0.375rem',
        '2xl': '0.375rem',
        '3xl': '0.375rem',
      },
      colors: {
        primary: {
          50: '#fbe9e7',
          100: '#ffccbc',
          200: '#ef9a9a',
          300: '#e57373',
          400: '#ef5350',
          500: '#e53935',
          600: '#d32f2f',
          700: '#c62828',
          800: '#b71c1c',
          900: '#7f0000',
        },
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
} satisfies Config

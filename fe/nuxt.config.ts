export default defineNuxtConfig({
  compatibilityDate: '2025-05-01',

  modules: ['@nuxtjs/tailwindcss'],

  runtimeConfig: {
    apiBase: process.env.API_BASE || 'http://localhost:8080',
  },

  devtools: { enabled: true },

  typescript: {
    strict: true,
  },

  tailwindcss: {
    configPath: 'tailwind.config.ts',
  },

  nitro: {
    routeRules: {
      '/api/query/chat': {
        headers: { 'X-Accel-Buffering': 'no' },
      },
      '/api/background-audits/**/stream': {
        headers: { 'X-Accel-Buffering': 'no' },
      },
    },
  },
})

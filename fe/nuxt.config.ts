export default defineNuxtConfig({
  compatibilityDate: '2025-05-01',

  modules: ['@nuxtjs/tailwindcss', 'reka-ui/nuxt'],

  runtimeConfig: {
    apiBase: process.env.API_BASE || 'http://localhost:8080',
  },

  app: {
    head: {
      title: 'Nexa',
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/nexa.svg' },
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap' },
      ],
    },
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

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: true,            // écoute sur toutes les interfaces
    port: 5173,
    allowedHosts: true,    // accepte l'adresse du tunnel Cloudflare
    proxy: {               // /api/search  ->  http://localhost:8000/search
      '/api': {
        target: 'http://localhost:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})

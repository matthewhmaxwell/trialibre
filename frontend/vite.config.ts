// Vite's defineConfig (NOT vitest's) — vitest's stricter ProxyServer
// types collide with vite's Server type on the `server.proxy` shape
// under `tsc -b`. The test config lives in a sibling `vitest.config.ts`
// so each tool's defineConfig sees only its own option surface.
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: './',  // Relative paths for static hosting on subdirectories
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})

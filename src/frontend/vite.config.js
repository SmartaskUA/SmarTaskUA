import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://api:8081",
        changeOrigin: true,
        secure: false,
        ws: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
    watch: {
      usePolling: true,
    },
    hmr: {
      overlay: true,
    },
    host: true,
    strictPort: true,
  },
  define: {
    global: 'globalThis'
  },
})

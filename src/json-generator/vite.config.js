import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/json-gen/',
  server: {
    port: 5174,
    host: true
  }
})

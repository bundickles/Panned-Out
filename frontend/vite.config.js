import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: process.env.PANNED_OUT_API_TARGET || 'http://127.0.0.1:8080',
        configure(proxy) {
          proxy.on('proxyReq', (proxyRequest, request) => {
            // Replace any caller-supplied value; the backend trusts this loopback proxy.
            proxyRequest.setHeader('X-Forwarded-For', request.socket.remoteAddress)
          })
        },
      },
    },
  },
})

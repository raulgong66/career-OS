/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
  server: {
    proxy: {
      '/profiles': { target: 'http://localhost:8000', changeOrigin: true },
      '/missions': { target: 'http://localhost:8000', changeOrigin: true },
      '/generate': { target: 'http://localhost:8000', changeOrigin: true },
      '/artifact-templates': { target: 'http://localhost:8000', changeOrigin: true },
      '/entities': { target: 'http://localhost:8000', changeOrigin: true },
      '/health': { target: 'http://localhost:8000', changeOrigin: true },
      '/version': { target: 'http://localhost:8000', changeOrigin: true },
      '/schemas': { target: 'http://localhost:8000', changeOrigin: true },
      '/validate': { target: 'http://localhost:8000', changeOrigin: true },
      '/create': { target: 'http://localhost:8000', changeOrigin: true },
      '/search': { target: 'http://localhost:8000', changeOrigin: true },
      '/optimize-cv': { target: 'http://localhost:8000', changeOrigin: true },
      '/analyze': { target: 'http://localhost:8000', changeOrigin: true },
      '/technologies': { target: 'http://localhost:8000', changeOrigin: true },
      '/interviews': { target: 'http://localhost:8000', changeOrigin: true },
      '/csks': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})

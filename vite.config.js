import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    historyApiFallback: {
      rewrites: [
        { from: /\/chapters\/.*/, to: '/index.html' }
      ]
    }
  }
})
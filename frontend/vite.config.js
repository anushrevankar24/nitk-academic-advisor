import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/chat':   { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/status': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/pdf':    { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/debug':  { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/admin':  { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});

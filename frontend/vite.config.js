import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// https://vite.dev/config/
export default defineConfig({
  // GitHub Pages serves the static demo under /<repo>/ (set VITE_BASE=/bust-detection/)
  base: process.env.VITE_BASE || '/',
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom')) {
            return 'react-vendor';
          }
          if (id.includes('historicalSummaryData')) {
            return 'historical-data';
          }
        },
      },
    },
    chunkSizeWarningLimit: 600,
  },
});

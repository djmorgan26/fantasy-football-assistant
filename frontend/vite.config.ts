/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      // Count every source file, not just the ones a test happened to import —
      // otherwise an entirely untested module is invisible rather than a zero.
      all: true,
      reporter: ['text', 'html'],
      // Only the code we author. Type declarations and the entry point are
      // either not executable or not meaningfully testable.
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.test.{ts,tsx}',
        'src/test/**',
        'src/main.tsx',
        'src/vite-env.d.ts',
        'src/types/**',
      ],
      /*
       * A ratchet, not an aspiration. Set just under what the suite actually
       * covers so a regression fails the build, and raise it as coverage
       * grows. (Vitest 0.34 reads these flat — a nested `thresholds` object is
       * 1.x syntax and is silently ignored here, which is how a threshold of
       * 55 sat in this file passing at 34.)
       *
       * Statements sit low because a large share of the tree is page and hook
       * wiring inherited from before the suite existed. Branches are the
       * number worth watching: it says the logic that *is* covered is covered
       * through its cases, not just executed once.
       */
      statements: 32,
      branches: 68,
      functions: 54,
      lines: 32,
    },
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
      '@/components': resolve(__dirname, './src/components'),
      '@/hooks': resolve(__dirname, './src/hooks'),
      '@/pages': resolve(__dirname, './src/pages'),
      '@/services': resolve(__dirname, './src/services'),
      '@/types': resolve(__dirname, './src/types'),
      '@/utils': resolve(__dirname, './src/utils'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
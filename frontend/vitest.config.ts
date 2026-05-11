// Vitest config — kept separate from `vite.config.ts` because vitest's
// `defineConfig` has a stricter `server.proxy` type than vite's, which
// breaks `tsc -b` in CI when the two are merged. Vitest auto-merges with
// the main vite config when running `vitest`, so plugins like @vitejs/
// plugin-react still apply for transforming components in tests.
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
    css: false,  // skip CSS parsing in tests
  },
})

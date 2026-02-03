import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    exclude: ['tests/**/pending_*.test.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['exospherehost/**/*.ts'],
      exclude: ['exospherehost/**/*.d.ts', 'tests/**/*']
    }
  }
});

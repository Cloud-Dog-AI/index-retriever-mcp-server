import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '/opt/iac/Development/cloud-dog-ai/cloud-dog-ai-ui-monorepo/apps/index-retriever/tests/e2e',
  timeout: 120_000,
  expect: {
    timeout: 30_000,
  },
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:8075',
    headless: true,
    trace: 'retain-on-failure',
  },
  reporter: [['list']],
});

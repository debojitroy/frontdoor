import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  retries: process.env.CI ? 1 : 0,
  use: { baseURL: "http://127.0.0.1:8143", trace: "retain-on-failure" },
  webServer: {
    command: "uv run python scripts/test_server.py",
    url: "http://127.0.0.1:8143/api/health",
    reuseExistingServer: false,
    timeout: 60000,
  },
});

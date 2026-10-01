/**
 * End-to-end tests of the owner cabinet against the real Python API.
 *
 *   npm run e2e                      # builds the cabinet, starts both servers
 *   E2E_SKIP_BUILD=1 npm run e2e     # reuse the last `next build`
 *
 * The API runs in development mode with in-memory storage, so each run starts
 * empty; login codes are read from its log (e2e/.artifacts/api.log). See
 * support/env.ts for ports and the Chromium override.
 */

import { mkdirSync } from "node:fs";
import path from "node:path";

import { defineConfig, devices } from "@playwright/test";

import {
  API_LOG_PATH,
  API_PORT,
  API_URL,
  ARTIFACTS_DIRECTORY,
  REPOSITORY_ROOT,
  WEB_DIRECTORY,
  WEB_PORT,
  WEB_URL,
} from "./support/env";

mkdirSync(ARTIFACTS_DIRECTORY, { recursive: true });

const isCI = Boolean(process.env.CI);
const skipBuild = process.env.E2E_SKIP_BUILD === "1";
const chromiumExecutable = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined;

/**
 * Login code providers and a database a developer may have in the shell:
 * with any of them the API would send codes for real or keep data between
 * runs, so the suite blanks them out.
 */
const UNSET_FOR_API = Object.fromEntries(
  [
    "DATABASE_URL",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM_NUMBER",
    "TWILIO_MESSAGING_SERVICE_SID",
    "TELEGRAM_GATEWAY_API_TOKEN",
    "WHATSAPP_OTP_PHONE_NUMBER_ID",
    "WHATSAPP_OTP_ACCESS_TOKEN",
    "WHATSAPP_OTP_TEMPLATE",
    "SMTP_HOST",
    "SMTP_FROM",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
  ].map((name) => [name, ""]),
);

export default defineConfig({
  testDir: ".",
  outputDir: path.join(ARTIFACTS_DIRECTORY, "results"),
  // One worker: the servers are shared and each test is a short user journey.
  workers: 1,
  fullyParallel: false,
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: isCI
    ? [["list"], ["html", { outputFolder: path.join(ARTIFACTS_DIRECTORY, "report"), open: "never" }]]
    : [["list"]],
  use: {
    baseURL: WEB_URL,
    locale: "en-US",
    timezoneId: "Europe/Berlin",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    launchOptions: chromiumExecutable ? { executablePath: chromiumExecutable } : {},
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } },
    },
  ],
  webServer: [
    {
      name: "api",
      // stdout and stderr go to a file the tests read login codes from.
      command: `uv run uvicorn app.main:create_application --factory --host 127.0.0.1 --port ${API_PORT} > "${API_LOG_PATH}" 2>&1`,
      cwd: REPOSITORY_ROOT,
      url: `${API_URL}/healthz`,
      env: {
        ...UNSET_FOR_API,
        APP_ENV: "development",
        OTP_LOG_CODES: "true",
        PYTHONUNBUFFERED: "1",
      },
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      name: "cabinet",
      command: `${skipBuild ? "" : "npm run build && "}npx next start --port ${WEB_PORT}`,
      cwd: WEB_DIRECTORY,
      url: `${WEB_URL}/login`,
      env: {
        BACKEND_URL: API_URL,
        COOKIE_SECURE: "false",
        NEXT_TELEMETRY_DISABLED: "1",
      },
      stdout: isCI ? "pipe" : "ignore",
      reuseExistingServer: false,
      timeout: 300_000,
    },
  ],
});

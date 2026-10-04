/**
 * End-to-end tests of the owner cabinet against the real Python API.
 *
 *   npm run e2e                      # builds the cabinet, starts both servers
 *   E2E_SKIP_BUILD=1 npm run e2e     # reuse the last `next build`
 *
 * The API runs in development mode with in-memory storage, so each run starts
 * with only the demo businesses (SEED_DEMO_DATA, used by live.spec.ts; every
 * other test signs up its own owner); login codes are read from its log
 * (e2e/.artifacts/api.log). See support/env.ts for ports and the Chromium
 * override.
 */

import { mkdirSync } from "node:fs";
import path from "node:path";

import { defineConfig, devices } from "@playwright/test";

import {
  API_LOG_PATH,
  API_PORT,
  API_URL,
  ARTIFACTS_DIRECTORY,
  E2E_VAPID_PRIVATE_KEY,
  E2E_VAPID_PUBLIC_KEY,
  PLATFORM_ADMIN_EMAIL,
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
    "TURNSTILE_SITE_KEY",
    "TURNSTILE_SECRET_KEY",
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
    // Animations jump to their end (CSS, motion and the landing's 3D hero,
    // which shows its still picture), so tests never wait on or race them.
    // A test about motion opts out: test.use({ contextOptions: { reducedMotion: "no-preference" } }).
    contextOptions: { reducedMotion: "reduce" },
    // The cabinet's service worker would take requests out of reach of
    // page.route(), which many tests use to stand in for the API; the
    // tests about it opt in: test.use({ serviceWorkers: "allow" }).
    serviceWorkers: "block",
    launchOptions: {
      ...(chromiumExecutable ? { executablePath: chromiumExecutable } : {}),
      // WebGL on machines without a GPU (CI): SwiftShader, asked for explicitly.
      args: ["--enable-unsafe-swiftshader"],
    },
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
        // The demo restaurant is live with its website chat on (live.spec.ts).
        SEED_DEMO_DATA: "true",
        // No model and no key: the rehearsal model plays the assistant, the
        // test customers and the judge, so "Apply changes" can pass its
        // checks (apply-changes.spec.ts) and a request for a person is
        // passed on (live.spec.ts).
        LLM_PROVIDER: "scripted",
        // Every test signs in from 127.0.0.1: lift the per-address caps.
        OTP_SENDS_PER_IP_PER_HOUR: "100000",
        OTP_VERIFIES_PER_IP_PER_10_MINUTES: "100000",
        OTP_SENDS_PER_COUNTRY_PER_HOUR: "100000",
        // The run's first platform admin signs in once per admin spec file
        // (and again after a worker restart): lift the per-address cap too.
        OTP_SENDS_PER_DESTINATION_PER_HOUR: "100000",
        // The run's first platform admin (the list only bootstraps the first
        // SUPER admin); the other test admins (admin-metrics.spec.ts,
        // two-factor.spec.ts, admin-system.spec.ts) are added to the team
        // by it, and all sign in with two factors (support/admin.ts).
        PLATFORM_ADMIN_EMAILS: PLATFORM_ADMIN_EMAIL,
        // Notification links lead to this cabinet; device notifications go
        // to the push service a test starts (notifications.spec.ts).
        CABINET_BASE_URL: WEB_URL,
        WEB_PUSH_VAPID_PUBLIC_KEY: E2E_VAPID_PUBLIC_KEY,
        WEB_PUSH_VAPID_PRIVATE_KEY: E2E_VAPID_PRIVATE_KEY,
        WEB_PUSH_VAPID_SUBJECT: "mailto:e2e@workshop.example",
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
        // The aw_locale cookie en-XA turns the texts long and accented (pseudo-locale.spec.ts).
        PSEUDO_LOCALE: "true",
      },
      stdout: isCI ? "pipe" : "ignore",
      reuseExistingServer: false,
      timeout: 300_000,
    },
  ],
});

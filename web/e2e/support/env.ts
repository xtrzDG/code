/**
 * Where the end-to-end servers run. Shared by playwright.config.ts (which
 * starts them) and the tests (which read the API log for login codes).
 *
 *   E2E_API_PORT     port of the Python API (default 8010)
 *   E2E_WEB_PORT     port of the cabinet (default 3010)
 *   E2E_SKIP_BUILD   "1": start the existing `.next` build instead of building
 *   PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH   a Chromium already on the machine
 */

import path from "node:path";

export const API_PORT = Number(process.env.E2E_API_PORT ?? 8010);
export const WEB_PORT = Number(process.env.E2E_WEB_PORT ?? 3010);

export const API_URL = `http://127.0.0.1:${API_PORT}`;
export const WEB_URL = `http://localhost:${WEB_PORT}`;

export const WEB_DIRECTORY = path.resolve(__dirname, "..", "..");
export const REPOSITORY_ROOT = path.resolve(WEB_DIRECTORY, "..");
/** Logs and Playwright output of a run (git-ignored). */
export const ARTIFACTS_DIRECTORY = path.join(WEB_DIRECTORY, "e2e", ".artifacts");
/** The API's stdout and stderr: development login codes are logged here. */
export const API_LOG_PATH = path.join(ARTIFACTS_DIRECTORY, "api.log");

/**
 * A VAPID key pair for the suite only (device notifications are on in the
 * test API): generated for these tests, never used anywhere else.
 */
export const E2E_VAPID_PUBLIC_KEY = "BCLJ-FEI59ekpdxEjnCQyhvo4e9t5e69gJwPrZLPLkp2tGkJ2aB6iqFph27ulfJ6h4Barq-NsmZFIumwXoK5RRE";
export const E2E_VAPID_PRIVATE_KEY = "TvFxPI0UYWj6Tk2K1oObluuz01W1zeWieAwrRpfzfhQ"; // gitleaks:allow

/** The API signs this address in as a platform admin (encryption-keys.spec.ts). */
export const PLATFORM_ADMIN_EMAIL = "platform-admin@e2e.workshop.example";
/** A second platform admin (admin-metrics.spec.ts): an address gets a code at most every 30 seconds. */
export const METRICS_ADMIN_EMAIL = "metrics-admin@e2e.workshop.example";
/** A platform admin who sets up the authenticator app through the sign-in page (two-factor.spec.ts). */
export const MFA_ADMIN_EMAIL = "mfa-admin@e2e.workshop.example";
/** A platform admin of the System page (admin-system.spec.ts). */
export const SYSTEM_ADMIN_EMAIL = "system-admin@e2e.workshop.example";

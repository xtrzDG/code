/**
 * Development login codes: with APP_ENV=development the API logs each code
 * ("Login code 123456 via email …") instead of sending it, without the phone
 * number or e-mail address. The tests read them from the API log that
 * playwright.config.ts writes; it runs one worker, so the newest code logged
 * after a test asked for one is that test's code.
 */

import { readFileSync, statSync } from "node:fs";

import { API_LOG_PATH } from "./env";

const CODE_LINE = /Login code (\d{6}) via (\w+)/g;
const POLL_INTERVAL_MS = 100;

/** The current length of the API log: pass it to `waitForLoginCode` as `since`. */
export function apiLogSize(): number {
  try {
    return statSync(API_LOG_PATH).size;
  } catch {
    return 0;
  }
}

/** The newest code logged after byte `since` (taken before asking for the code). */
export async function waitForLoginCode({ since, timeoutMs = 15_000 }: { since: number; timeoutMs?: number }): Promise<string> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const fresh = readFileSync(API_LOG_PATH).subarray(since).toString("utf8");
    const code = [...fresh.matchAll(CODE_LINE)].map((match) => match[1]).at(-1);
    if (code) {
      return code;
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }
  throw new Error(`No login code appeared in ${API_LOG_PATH} within ${timeoutMs} ms.`);
}

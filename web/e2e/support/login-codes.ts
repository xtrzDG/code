/**
 * Development login codes: with APP_ENV=development the API logs each code
 * ("Login code 123456 for o***r@x.example via email …") instead of sending
 * it. The tests read them from the API log that playwright.config.ts writes.
 */

import { readFileSync, statSync } from "node:fs";

import { API_LOG_PATH } from "./env";

const CODE_LINE = /Login code (\d{6}) for (.+?) via (\w+)/g;
const POLL_INTERVAL_MS = 100;

/** The current length of the API log: pass it to `waitForLoginCode` as `since`. */
export function apiLogSize(): number {
  try {
    return statSync(API_LOG_PATH).size;
  } catch {
    return 0;
  }
}

/**
 * The newest code logged after byte `since` for a destination whose masked
 * form ends with `destinationSuffix`: the e-mail domain, or the last two
 * digits of a phone number (the only digits the API leaves visible).
 */
export async function waitForLoginCode({
  since,
  destinationSuffix,
  timeoutMs = 15_000,
}: {
  since: number;
  destinationSuffix: string;
  timeoutMs?: number;
}): Promise<string> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const fresh = readFileSync(API_LOG_PATH).subarray(since).toString("utf8");
    const codes = [...fresh.matchAll(CODE_LINE)]
      .filter((match) => match[2]?.trimEnd().endsWith(destinationSuffix))
      .map((match) => match[1]);
    const code = codes.at(-1);
    if (code) {
      return code;
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }
  throw new Error(`No login code for "…${destinationSuffix}" appeared in ${API_LOG_PATH} within ${timeoutMs} ms.`);
}

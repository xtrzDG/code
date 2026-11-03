/**
 * The API's wall clock as the tests see it. It is this machine's clock,
 * except in the visual tests: their API (scripts/visual_api.py) starts its
 * clock at a fixed moment and logs its first reading ("Visual clock: <its
 * s.nnnnnnnnn> s at the machine's <s.nnnnnnnnn> s": seconds with nine
 * decimals, which the log's card number masking leaves alone), so whatever
 * depends on the API's time (an authenticator code, support/totp.ts) reads
 * it from here.
 */

import { readFileSync } from "node:fs";

import { API_LOG_PATH } from "./env";

const CLOCK_LINE = /Visual clock: (\d+)\.(\d{9}) s at the machine's (\d+)\.(\d{9}) s/;
const NANOSECONDS_PER_SECOND = 1_000_000_000n;
const NANOSECONDS_PER_MILLISECOND = 1_000_000n;

/** "1793030000.123456789" (seconds, nine decimals) in nanoseconds. */
function nanoseconds(whole: string, fraction: string): bigint {
  return BigInt(whole) * NANOSECONDS_PER_SECOND + BigInt(fraction);
}

/** How far the API's clock is ahead of this machine's, in ms, by the log's first clock line (0 without one). */
export function clockOffsetMs(log: string): number {
  const match = CLOCK_LINE.exec(log);
  if (!match) {
    return 0;
  }
  const api = nanoseconds(match[1]!, match[2]!);
  const machine = nanoseconds(match[3]!, match[4]!);
  return Number((api - machine) / NANOSECONDS_PER_MILLISECOND);
}

let knownOffsetMs: number | undefined;

/** The API's clock offset in this run (read once the API has logged it). */
function apiClockOffsetMs(): number {
  if (knownOffsetMs !== undefined) {
    return knownOffsetMs;
  }
  let log = "";
  try {
    log = readFileSync(API_LOG_PATH, "utf8");
  } catch {
    return 0;
  }
  const offset = clockOffsetMs(log);
  if (offset !== 0) {
    knownOffsetMs = offset;
  }
  return offset;
}

/** "Now" on the API's clock, in ms since the epoch. */
export function apiNow(): number {
  return Date.now() + apiClockOffsetMs();
}

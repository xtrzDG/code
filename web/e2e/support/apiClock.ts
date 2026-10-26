/**
 * The API's wall clock as the tests see it. It is this machine's clock,
 * except in the visual tests: their API (scripts/visual_api.py) starts its
 * clock at a fixed moment and logs its first reading ("Visual clock: <its
 * ns> ns at the machine's <ns> ns"), so whatever depends on the API's time
 * (an authenticator code, support/totp.ts) reads it from here.
 */

import { readFileSync } from "node:fs";

import { API_LOG_PATH } from "./env";

const CLOCK_LINE = /Visual clock: (\d+) ns at the machine's (\d+) ns/;
const NANOSECONDS_PER_MILLISECOND = 1_000_000n;

/** How far the API's clock is ahead of this machine's, in ms, by the log's first clock line (0 without one). */
export function clockOffsetMs(log: string): number {
  const match = CLOCK_LINE.exec(log);
  if (!match) {
    return 0;
  }
  return Number((BigInt(match[1]!) - BigInt(match[2]!)) / NANOSECONDS_PER_MILLISECOND);
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

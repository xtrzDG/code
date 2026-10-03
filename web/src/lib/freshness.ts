/**
 * How fresh a page's data is, for the "Updated just now" line that took
 * the place of the Refresh buttons: just now under a minute, minutes up to
 * an hour, then the clock time.
 */

export type Freshness =
  | { kind: "never" }
  | { kind: "justNow" }
  | { kind: "minutes"; minutes: number }
  | { kind: "at"; at: Date };

const MINUTE_MS = 60_000;
const HOUR_MS = 60 * MINUTE_MS;

/** `updatedAt` and `now` in milliseconds since the epoch (0: never loaded). */
export function freshness(updatedAt: number, now: number): Freshness {
  if (updatedAt <= 0) {
    return { kind: "never" };
  }
  const age = Math.max(0, now - updatedAt);
  if (age < MINUTE_MS) {
    return { kind: "justNow" };
  }
  if (age < HOUR_MS) {
    return { kind: "minutes", minutes: Math.floor(age / MINUTE_MS) };
  }
  return { kind: "at", at: new Date(updatedAt) };
}

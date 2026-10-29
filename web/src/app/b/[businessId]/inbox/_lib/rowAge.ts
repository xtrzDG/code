/**
 * How long ago a row's last message came, short enough for the meta line
 * ("now", "5 min", "3 h", "2 d"); from a week on the row shows the date.
 * The exact time is in the row's details.
 */

export type RowAge = { unit: "now" } | { unit: "minutes" | "hours" | "days"; count: number };

const MINUTE_MS = 60_000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;
/** From this age on the date reads better than "8 d". */
const DATE_FROM_MS = 7 * DAY_MS;

/** The age of a timestamp in microseconds at `nowMs`, or null when the date should show. */
export function rowAge(timestampMicros: number, nowMs: number): RowAge | null {
  const age = Math.max(0, nowMs - timestampMicros / 1000);
  if (age >= DATE_FROM_MS) {
    return null;
  }
  if (age < MINUTE_MS) {
    return { unit: "now" };
  }
  if (age < HOUR_MS) {
    return { unit: "minutes", count: Math.floor(age / MINUTE_MS) };
  }
  if (age < DAY_MS) {
    return { unit: "hours", count: Math.floor(age / HOUR_MS) };
  }
  return { unit: "days", count: Math.floor(age / DAY_MS) };
}

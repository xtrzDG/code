/**
 * The admin forms' times: `<input type="datetime-local">` values in the
 * admin's own time zone, and the API's UNIX microseconds.
 */

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

/** UNIX microseconds → "2026-10-04T09:30" in the device's time zone (what datetime-local shows). */
export function microsToLocalInput(micros: number): string {
  const date = new Date(Math.floor(micros / 1000));
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** "2026-10-04T09:30" in the device's time zone → UNIX microseconds; null when it is not a time. */
export function localInputToMicros(value: string): number | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value.trim());
  if (!match) {
    return null;
  }
  const [year, month, day, hour, minute] = match.slice(1).map(Number) as [number, number, number, number, number];
  const date = new Date(year, month - 1, day, hour, minute);
  if (date.getMonth() !== month - 1 || date.getDate() !== day) {
    return null;
  }
  return date.getTime() * 1000;
}

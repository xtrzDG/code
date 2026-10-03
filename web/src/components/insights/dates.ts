/**
 * Calendar helpers for the business time zone.
 *
 * The API speaks two kinds of time: instants as UNIX microseconds, and local
 * calendar values of the business ("2026-10-02", "20:00") already in its
 * time zone. Local values are formatted as UTC so the browser's own time
 * zone never shifts them.
 */

import { toDate, type Timestamp } from "@/lib/format";
import { dateTimeFormat, relativeTimeFormat } from "@/lib/intl/formatters";

/** "YYYY-MM-DD" in the business time zone (the API's LocalDate). */
export type LocalDateText = string;

const LOCAL_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;
const LOCAL_TIME = /^([01]\d|2[0-3]):([0-5]\d)$/;

export function isLocalDate(text: string): boolean {
  const match = LOCAL_DATE.exec(text);
  if (!match) {
    return false;
  }
  const date = localDateToUtc(text);
  return date.toISOString().slice(0, 10) === text;
}

export function isLocalTime(text: string): boolean {
  return LOCAL_TIME.test(text);
}

/** "2026-10-02" -> Date at 00:00 UTC of that day. */
export function localDateToUtc(date: LocalDateText): Date {
  const [year, month, day] = date.split("-").map(Number);
  return new Date(Date.UTC(year ?? 1970, (month ?? 1) - 1, day ?? 1));
}

/** The calendar date of an instant in a time zone: "2026-10-02". */
export function localDateOf(value: Timestamp, timeZone: string): LocalDateText {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(toDate(value));
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find((item) => item.type === type)?.value ?? "";
  return `${part("year")}-${part("month")}-${part("day")}`;
}

/** Today in the business time zone. */
export function todayIn(timeZone: string, now: Date = new Date()): LocalDateText {
  return localDateOf(now, timeZone);
}

/** Calendar arithmetic: addDays("2026-02-28", 1) -> "2026-03-01". */
export function addDays(date: LocalDateText, days: number): LocalDateText {
  const result = localDateToUtc(date);
  result.setUTCDate(result.getUTCDate() + days);
  return result.toISOString().slice(0, 10);
}

/** Whole days from `from` to `to` (negative when `to` is earlier). */
export function daysBetween(from: LocalDateText, to: LocalDateText): number {
  return Math.round((localDateToUtc(to).getTime() - localDateToUtc(from).getTime()) / 86_400_000);
}

/** "2026-10-02" as text in the locale ("Fri, Oct 2"); never shifted by the browser's zone. */
export function formatLocalDate(
  date: LocalDateText,
  locale: string,
  options: Intl.DateTimeFormatOptions = { dateStyle: "medium" },
): string {
  if (!isLocalDate(date)) {
    return date;
  }
  return dateTimeFormat(locale, { ...options, timeZone: "UTC" }).format(localDateToUtc(date));
}

/** "20:00" in the locale's clock ("8:00 PM" in English, "20:00" in Russian). */
export function formatLocalTime(time: string, locale: string): string {
  const match = LOCAL_TIME.exec(time);
  if (!match) {
    return time;
  }
  const date = new Date(Date.UTC(2024, 0, 1, Number(match[1]), Number(match[2])));
  return dateTimeFormat(locale, { hour: "numeric", minute: "2-digit", timeZone: "UTC" }).format(date);
}

/** A range of local dates as one short text: "Sep 2 – Oct 1, 2026". */
export function formatLocalDateRange(from: LocalDateText, to: LocalDateText, locale: string): string {
  if (!isLocalDate(from) || !isLocalDate(to)) {
    return `${from} – ${to}`;
  }
  const format = dateTimeFormat(locale, { dateStyle: "medium", timeZone: "UTC" });
  return format.formatRange(localDateToUtc(from), localDateToUtc(to));
}

const RELATIVE_STEPS: readonly { unit: Intl.RelativeTimeFormatUnit; seconds: number }[] = [
  { unit: "day", seconds: 86_400 },
  { unit: "hour", seconds: 3_600 },
  { unit: "minute", seconds: 60 },
];

/**
 * "5 minutes ago", "yesterday" for instants within `maxDays`; null for
 * older ones (show the date instead).
 */
export function formatRelative(
  value: Timestamp,
  locale: string,
  options: { now?: Date; maxDays?: number } = {},
): string | null {
  const now = options.now ?? new Date();
  const seconds = Math.round((toDate(value).getTime() - now.getTime()) / 1000);
  if (Math.abs(seconds) > (options.maxDays ?? 7) * 86_400) {
    return null;
  }
  const format = relativeTimeFormat(locale, { numeric: "auto" });
  if (Math.abs(seconds) < 60) {
    return format.format(0, "second");
  }
  for (const step of RELATIVE_STEPS) {
    if (Math.abs(seconds) >= step.seconds) {
      return format.format(Math.trunc(seconds / step.seconds), step.unit);
    }
  }
  return format.format(seconds, "second");
}

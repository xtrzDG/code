/**
 * Dates and times of a guest's booking page (/r/{token}). The API gives
 * the booking's local date ("2026-10-06") and time ("19:00") in the
 * business's zone; they are written in the guest's language as they are,
 * read as a UTC wall clock, so neither the server's nor the guest's own
 * zone moves them.
 */

import type { Schema } from "@/api/types";

import { capitalizeFirst, formatDate, formatTime } from "../format";
import { calendarParts } from "../intl/calendarFields";

type ManagedBookingView = Schema<"ManagedBookingView">;

const LOCAL_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;
const LOCAL_TIME = /^(\d{2}):(\d{2})$/;

/** A local date and time as the same wall clock in UTC; null for malformed text. */
export function wallClock(date: string, time = "00:00"): Date | null {
  const day = LOCAL_DATE.exec(date);
  const clock = LOCAL_TIME.exec(time);
  if (!day || !clock) {
    return null;
  }
  return new Date(Date.UTC(Number(day[1]), Number(day[2]) - 1, Number(day[3]), Number(clock[1]), Number(clock[2])));
}

/** "Tuesday, October 6, 2026" in the language (the text itself when malformed). */
export function formatLocalDate(date: string, language: string): string {
  const moment = wallClock(date);
  return moment
    ? capitalizeFirst(formatDate(moment, { locale: language, timeZone: "UTC", dateStyle: "full" }), language)
    : date;
}

/** "7:00 PM" in English, "19:00" in Russian (the text itself when malformed). */
export function formatLocalTime(time: string, language: string): string {
  const moment = wallClock("2000-01-01", time);
  return moment ? formatTime(moment, { locale: language, timeZone: "UTC" }) : time;
}

export interface BookingWhen {
  /** The visit's day, or the stay's arrival day. */
  date: string;
  /** "7:00 PM – 9:00 PM" for a time slot; null for a stay. */
  times: string | null;
  /** The departure day of a stay; null for a time slot. */
  departure: string | null;
}

/** When the booking is, as the page writes it. */
export function bookingWhen(view: ManagedBookingView, language: string): BookingWhen {
  const date = formatLocalDate(view.date, language);
  if (view.booking_unit === "night") {
    return { date, times: null, departure: formatLocalDate(view.end_date, language) };
  }
  if (!view.time) {
    return { date, times: null, departure: null };
  }
  const start = formatLocalTime(view.time, language);
  if (!view.end_time) {
    return { date, times: start, departure: null };
  }
  const end = formatLocalTime(view.end_time, language);
  const times =
    view.end_date === view.date ? `${start} – ${end}` : `${start} – ${formatLocalDate(view.end_date, language)} ${end}`;
  return { date, times, departure: null };
}

/** A new time as the Move button names it: "Wednesday, October 7, 2026, 8:00 PM". */
export function moveTarget(date: string, time: string | null, language: string): string {
  const day = formatLocalDate(date, language);
  return time ? `${day}, ${formatLocalTime(time, language)}` : day;
}

/** Today's date in the business's zone ("2026-10-05"); UTC for an unknown zone. */
export function todayIn(timeZone: string, now: Date): string {
  const fields: Intl.DateTimeFormatOptions = { year: "numeric", month: "2-digit", day: "2-digit" };
  let parts: Partial<Record<Intl.DateTimeFormatPartTypes, string>>;
  try {
    parts = calendarParts(now, timeZone, fields, "en-CA");
  } catch {
    parts = calendarParts(now, "UTC", fields, "en-CA");
  }
  return `${parts.year}-${parts.month}-${parts.day}`;
}

/** Fill `{name}` placeholders: fillPlaceholders("Move to {when}", { when: "…" }). */
export function fillPlaceholders(template: string, values: Readonly<Record<string, string>>): string {
  return template.replace(/\{(\w+)\}/g, (whole, name: string) => values[name] ?? whole);
}

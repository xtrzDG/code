/**
 * The local days a calendar view shows, in the business time zone: one day,
 * the week around a date (starting on the locale's first weekday), or two
 * weeks of nights from a date; and where the arrows go from there.
 */

import { addDays, formatLocalDate, type LocalDateText } from "@/components/insights/dates";
import type { IsoWeekday } from "@/lib/intl/localeCalendar";

import type { CalendarView } from "./calendarTypes";

/** Nights shown by the hotel grid: two weeks, the usual horizon of a front desk. */
export const NIGHTS_SHOWN = 14;

/** The ISO weekday (1 = Monday … 7 = Sunday) of a local date. */
export function isoWeekdayOf(date: LocalDateText): IsoWeekday {
  const day = new Date(`${date}T00:00:00Z`).getUTCDay();
  return (day === 0 ? 7 : day) as IsoWeekday;
}

/** The first day of the week that holds `date`. */
export function weekStartOf(date: LocalDateText, firstDay: IsoWeekday): LocalDateText {
  const offset = (isoWeekdayOf(date) - firstDay + 7) % 7;
  return addDays(date, -offset);
}

/** The window of local days a view reads from the API. */
export function calendarWindow(
  view: CalendarView,
  anchor: LocalDateText,
  firstDay: IsoWeekday,
): { from: LocalDateText; days: number } {
  switch (view) {
    case "week":
      return { from: weekStartOf(anchor, firstDay), days: 7 };
    case "nights":
      return { from: anchor, days: NIGHTS_SHOWN };
    default:
      return { from: anchor, days: 1 };
  }
}

/** The date the arrows lead to: a day back or on, or a week for the week and the nights. */
export function shiftAnchor(view: CalendarView, anchor: LocalDateText, step: -1 | 1): LocalDateText {
  return addDays(anchor, view === "day" ? step : 7 * step);
}

/** Every local date of a window, in order. */
export function windowDates(from: LocalDateText, days: number): LocalDateText[] {
  return Array.from({ length: days }, (_, index) => addDays(from, index));
}

/**
 * "Oct 5 – Oct 11, 2026": two dates of the locale joined by a dash. Not
 * Intl's formatRange, whose spacing differs between the server's ICU and
 * the browser's (the heading is rendered on both).
 */
export function formatDateSpan(from: LocalDateText, to: LocalDateText, locale: string): string {
  const start = formatLocalDate(from, locale, { day: "numeric", month: "short" });
  return `${start} – ${formatLocalDate(to, locale, { day: "numeric", month: "short", year: "numeric" })}`;
}

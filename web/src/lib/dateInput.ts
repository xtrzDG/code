/**
 * Calendar dates as a form edits them: the value is ISO ("2026-10-06")
 * whatever the cabinet's language; people read the date in the locale
 * ("6 окт. 2026 г.", "6 ოქტ. 2026", "Oct 6, 2026") and pick it from a month
 * whose week starts where the locale starts it.
 *
 * `parseTypedDate` understands what people type: ISO, numbers in the
 * locale's order ("06.10.2026" in Russian, "10/06/2026" in English, a
 * two-digit year, no year for this year) and month names ("6 окт 2026").
 */

import { capitalizeFirst } from "./format";
import { dateTimeFormat } from "./intl/formatters";
import { dateFieldOrder, firstDayOfWeek, monthNames, type IsoWeekday } from "./intl/localeCalendar";

/** "YYYY-MM-DD". */
export type IsoDate = string;

const ISO_DATE = /^(\d{4})-(\d{1,2})-(\d{1,2})$/;

interface DayParts {
  year: number;
  month: number;
  day: number;
}

function utcOf({ year, month, day }: DayParts): Date {
  const date = new Date(Date.UTC(2000, 0, 1));
  date.setUTCFullYear(year, month - 1, day);
  return date;
}

function isoOf(date: Date): IsoDate {
  return `${String(date.getUTCFullYear()).padStart(4, "0")}-${String(date.getUTCMonth() + 1).padStart(2, "0")}-${String(date.getUTCDate()).padStart(2, "0")}`;
}

/** A real calendar day as ISO, or null (31 February is not one). */
function validIso(parts: DayParts): IsoDate | null {
  if (parts.year < 1000 || parts.year > 9999 || parts.month < 1 || parts.month > 12 || parts.day < 1 || parts.day > 31) {
    return null;
  }
  const date = utcOf(parts);
  return date.getUTCMonth() === parts.month - 1 && date.getUTCDate() === parts.day ? isoOf(date) : null;
}

/** The parts of an ISO date, or null when it is not one. */
export function isoParts(value: string): DayParts | null {
  const match = ISO_DATE.exec(value.trim());
  if (!match) {
    return null;
  }
  const parts = { year: Number(match[1]), month: Number(match[2]), day: Number(match[3]) };
  return validIso(parts) === null ? null : parts;
}

export function isIsoDate(value: string): boolean {
  return ISO_DATE.test(value) && isoParts(value) !== null && value.length === 10;
}

export function addDaysIso(value: IsoDate, days: number): IsoDate {
  const parts = isoParts(value);
  if (!parts) {
    return value;
  }
  const date = utcOf(parts);
  date.setUTCDate(date.getUTCDate() + days);
  return isoOf(date);
}

/** A month later or earlier, on the same day or the month's last one (31 Jan + 1 month = 29 Feb in 2028). */
export function addMonthsIso(value: IsoDate, months: number): IsoDate {
  const parts = isoParts(value);
  if (!parts) {
    return value;
  }
  const index = parts.year * 12 + (parts.month - 1) + months;
  const year = Math.floor(index / 12);
  const month = (index % 12) + 1;
  const last = utcOf({ year, month: month + 1, day: 0 }).getUTCDate();
  return isoOf(utcOf({ year, month, day: Math.min(parts.day, last) }));
}

/** Within the bounds (either may be missing or empty). */
export function clampIso(value: IsoDate, min?: string | null, max?: string | null): IsoDate {
  if (min && isIsoDate(min) && value < min) {
    return min;
  }
  if (max && isIsoDate(max) && value > max) {
    return max;
  }
  return value;
}

export function isWithin(value: IsoDate, min?: string | null, max?: string | null): boolean {
  return clampIso(value, min, max) === value;
}

/** The device's own calendar day (a date picker's "today" when nothing more exact is known). */
export function deviceToday(now: Date = new Date()): IsoDate {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

/** A date as the locale writes it: "6 окт. 2026 г.", "Oct 6, 2026"; "" for no date. */
export function dateText(value: IsoDate, locale: string, style: "medium" | "long" | "full" = "medium"): string {
  const parts = isoParts(value);
  return parts ? dateTimeFormat(locale, { dateStyle: style, timeZone: "UTC" }).format(utcOf(parts)) : "";
}

/** A month's title: "Октябрь 2026 г.", "October 2026", "ოქტომბერი, 2026". */
export function monthTitle(year: number, month: number, locale: string): string {
  const text = dateTimeFormat(locale, { month: "long", year: "numeric", timeZone: "UTC" }).format(utcOf({ year, month, day: 1 }));
  return capitalizeFirst(text, locale);
}

/** The weekdays of a calendar's columns, from the locale's first day of the week. */
export function weekColumns(locale: string): IsoWeekday[] {
  const first = firstDayOfWeek(locale);
  return Array.from({ length: 7 }, (_, index) => (((first - 1 + index) % 7) + 1) as IsoWeekday);
}

/** The weeks of a month as rows of seven days (null outside the month), starting on `firstDay`. */
export function monthWeeks(year: number, month: number, firstDay: IsoWeekday): (IsoDate | null)[][] {
  const first = utcOf({ year, month, day: 1 });
  const isoWeekday = first.getUTCDay() === 0 ? 7 : first.getUTCDay();
  const lead = (isoWeekday - firstDay + 7) % 7;
  const length = utcOf({ year, month: month + 1, day: 0 }).getUTCDate();
  const cells: (IsoDate | null)[] = [
    ...Array.from({ length: lead }, () => null),
    ...Array.from({ length }, (_, index) => isoOf(utcOf({ year, month, day: index + 1 }))),
  ];
  while (cells.length % 7 !== 0) {
    cells.push(null);
  }
  return Array.from({ length: cells.length / 7 }, (_, row) => cells.slice(row * 7, row * 7 + 7));
}

const ENGLISH_MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];

/** Lower case without a closing abbreviation mark ("окт.", Hebrew "אוק׳"). */
const normalizeWord = (word: string): string => word.toLowerCase().replace(/[.׳'’]+$/, "");

/** The month a word names (1–12): a month name of the locale or English, whole or its first three letters. */
function monthOfWord(word: string, locale: string): number | null {
  // Hebrew dates join "in" to the month: "6 באוק׳ 2026".
  const typed = normalizeWord(word).replace(/^ב(?=[\u05d0-\u05ea]{3})/, "");
  if (typed.length < 3) {
    return null;
  }
  const { long, short, standalone } = monthNames(locale);
  for (let index = 0; index < 12; index += 1) {
    const names = [long[index], short[index], standalone[index], ENGLISH_MONTHS[index]].map((name) => normalizeWord(name ?? ""));
    if (names.some((name) => name.length >= 3 && (name.startsWith(typed) || typed.startsWith(name.slice(0, 3))))) {
      return index + 1;
    }
  }
  return null;
}

const fullYear = (text: string): number => (text.length <= 2 ? 2000 + Number(text) : Number(text));

/**
 * A date typed by a person as ISO, or null. Numbers follow the locale's
 * order of day, month and year; a missing year is the year of `today`.
 */
export function parseTypedDate(text: string, locale: string, today: IsoDate = deviceToday()): IsoDate | null {
  const trimmed = text.trim();
  if (ISO_DATE.test(trimmed)) {
    const parts = isoParts(trimmed);
    return parts ? validIso(parts) : null;
  }
  const tokens = trimmed.split(/[\s.,/\-–]+/).filter(Boolean);
  const numbers = tokens.filter((token) => /^\d+$/.test(token));
  const words = tokens.filter((token) => !/^\d+$/.test(token));
  const thisYear = isoParts(today)?.year ?? new Date().getFullYear();
  if (numbers.some((number) => number.length > 4) || numbers.length === 0) {
    return null;
  }
  const months = words.map((word) => monthOfWord(word, locale)).filter((month): month is number => month !== null);
  if (months.length > 1) {
    return null;
  }
  const month = months[0];
  if (month !== undefined) {
    // "6 окт. 2026 г.", "Oct 6, 2026", "6 ოქტ": a day, maybe a year.
    const year = numbers.find((number) => number.length === 4);
    const days = numbers.filter((number) => number !== year);
    if (days.length !== 1 || numbers.length > 2) {
      return null;
    }
    return validIso({ year: year ? Number(year) : thisYear, month, day: Number(days[0]) });
  }
  if (words.length > 0 || numbers.length < 2 || numbers.length > 3) {
    return null;
  }
  const order = dateFieldOrder(locale).filter((part) => numbers.length === 3 || part !== "year");
  const value = (part: "day" | "month" | "year"): number => {
    const index = order.indexOf(part);
    const token = numbers[index] ?? "";
    return part === "year" ? fullYear(token) : Number(token);
  };
  return validIso({ year: numbers.length === 3 ? value("year") : thisYear, month: value("month"), day: value("day") });
}

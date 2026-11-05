/**
 * Georgian dates and times as CLDR writes them ("6 ოქტ. 2026, 17:05",
 * "სამშაბათი, 6 ოქტომბერი"), built from the calendar fields the English
 * Intl of every browser reads in any time zone. See `georgianData.ts` for
 * why. Option sets it does not cover (time zone names, 12-hour clocks,
 * narrow names) return null, and the caller asks the browser's Intl.
 */

import { MONTHS_LONG, MONTHS_SHORT, WEEKDAYS_LONG, WEEKDAYS_SHORT } from "./georgianData";

interface Fields {
  year: number;
  /** 1 = January. */
  month: number;
  day: number;
  /** 0 = Sunday. */
  weekday: number;
  hour: number;
  minute: number;
  second: number;
}

type Pattern = (fields: Fields) => string;

export interface GeorgianDateFormat {
  format(date: Date): string;
  formatRange(from: Date, to: Date): string;
}

const SUPPORTED_OPTIONS = new Set([
  "dateStyle",
  "timeStyle",
  "timeZone",
  "weekday",
  "year",
  "month",
  "day",
  "hour",
  "minute",
  "second",
  "hourCycle",
  "hour12",
  "localeMatcher",
  "formatMatcher",
]);

const two = (value: number): string => String(value).padStart(2, "0");

function fieldReader(timeZone: string | undefined): (date: Date) => Fields {
  const english = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "numeric",
    minute: "numeric",
    second: "numeric",
    hourCycle: "h23",
  });
  return (date) => {
    const values: Partial<Record<Intl.DateTimeFormatPartTypes, number>> = {};
    for (const part of english.formatToParts(date)) {
      values[part.type] = Number(part.value);
    }
    const year = values.year ?? 1970;
    const month = values.month ?? 1;
    const day = values.day ?? 1;
    const calendarDay = new Date(0);
    calendarDay.setUTCFullYear(year, month - 1, day);
    return {
      year,
      month,
      day,
      weekday: calendarDay.getUTCDay(),
      hour: (values.hour ?? 0) % 24,
      minute: values.minute ?? 0,
      second: values.second ?? 0,
    };
  };
}

function dateStylePattern(style: NonNullable<Intl.DateTimeFormatOptions["dateStyle"]>): Pattern {
  switch (style) {
    case "full":
      return (f) => `${WEEKDAYS_LONG[f.weekday]}, ${two(f.day)} ${MONTHS_LONG[f.month - 1]}, ${f.year}`;
    case "long":
      return (f) => `${f.day} ${MONTHS_LONG[f.month - 1]}, ${f.year}`;
    case "medium":
      return (f) => `${f.day} ${MONTHS_SHORT[f.month - 1]}. ${f.year}`;
    case "short":
      return (f) => `${two(f.day)}.${two(f.month)}.${two(f.year % 100)}`;
  }
}

function timeStylePattern(style: NonNullable<Intl.DateTimeFormatOptions["timeStyle"]>): Pattern | null {
  if (style === "short") {
    return (f) => `${two(f.hour)}:${two(f.minute)}`;
  }
  // Long and full times name the time zone: left to the browser's Intl.
  return style === "medium" ? (f) => `${two(f.hour)}:${two(f.minute)}:${two(f.second)}` : null;
}

const numeric = (width: "numeric" | "2-digit" | undefined, value: number): string =>
  width === "2-digit" ? two(value % 100) : String(value);

/** "6 ოქტ. 2026", "სამ, 6 ოქტ", "6.10.2026"; null when the fields make no Georgian pattern. */
function datePattern(options: Intl.DateTimeFormatOptions): Pattern | null {
  const { weekday, year, day } = options;
  const month = options.month;
  if ((weekday !== undefined && weekday !== "long" && weekday !== "short") || month === "narrow") {
    return null;
  }
  const weekdays = weekday === "long" ? WEEKDAYS_LONG : WEEKDAYS_SHORT;
  const withWeekday = (core: Pattern): Pattern | null => {
    if (weekday === undefined) {
      return core;
    }
    return day === undefined ? null : (f) => `${weekdays[f.weekday]}, ${core(f)}`;
  };
  if (month === "long" || month === "short") {
    const names = month === "long" ? MONTHS_LONG : MONTHS_SHORT;
    const beforeYear = month === "short" ? ". " : ", ";
    const name = (f: Fields): string => names[f.month - 1] ?? "";
    const dayPart = (f: Fields): string => (day === undefined ? "" : `${numeric(day, f.day)} `);
    const yearPart = (f: Fields): string => (year === undefined ? "" : `${beforeYear}${numeric(year, f.year)}`);
    return withWeekday((f) => `${dayPart(f)}${name(f)}${yearPart(f)}`);
  }
  if (month === "numeric" || month === "2-digit") {
    return withWeekday((f) =>
      [
        day === undefined ? null : numeric(day, f.day),
        numeric(month, f.month),
        year === undefined ? null : numeric(year, f.year),
      ]
        .filter((part) => part !== null)
        .join("."),
    );
  }
  if (day !== undefined && year !== undefined) {
    return null;
  }
  if (day !== undefined) {
    return weekday === undefined ? (f) => numeric(day, f.day) : null;
  }
  if (year !== undefined) {
    return weekday === undefined ? (f) => numeric(year, f.year) : null;
  }
  return (f) => weekdays[f.weekday] ?? "";
}

/** "17:05", "9:03", "09:03:07"; null for 12-hour clocks and minutes without hours. */
function timePattern(options: Intl.DateTimeFormatOptions): Pattern | null {
  const { hour, minute, second } = options;
  if (options.hour12 === true || (options.hourCycle !== undefined && options.hourCycle !== "h23")) {
    return null;
  }
  if (hour === undefined || (second !== undefined && minute === undefined)) {
    return null;
  }
  if (minute === undefined) {
    return (f) => two(f.hour);
  }
  const hours = (f: Fields): string => (hour === "2-digit" ? two(f.hour) : String(f.hour));
  return second === undefined
    ? (f) => `${hours(f)}:${two(f.minute)}`
    : (f) => `${hours(f)}:${two(f.minute)}:${two(f.second)}`;
}

function joined(date: Pattern | null, time: Pattern | null): Pattern {
  return (f) => [date?.(f), time?.(f)].filter((part) => part !== undefined).join(", ");
}

function patternOf(options: Intl.DateTimeFormatOptions): Pattern | null {
  if (Object.keys(options).some((key) => !SUPPORTED_OPTIONS.has(key))) {
    return null;
  }
  const { dateStyle, timeStyle, weekday, year, month, day, hour, minute, second } = options;
  const hasDateFields = [weekday, year, month, day].some((value) => value !== undefined);
  const hasTimeFields = [hour, minute, second].some((value) => value !== undefined);
  if (dateStyle !== undefined || timeStyle !== undefined) {
    if (hasDateFields || hasTimeFields) {
      return null;
    }
    const time = timeStyle === undefined ? null : timeStylePattern(timeStyle);
    if (timeStyle !== undefined && time === null) {
      return null;
    }
    return joined(dateStyle === undefined ? null : dateStylePattern(dateStyle), time);
  }
  if (!hasDateFields && !hasTimeFields) {
    return datePattern({ year: "numeric", month: "numeric", day: "numeric" });
  }
  const date = hasDateFields ? datePattern(options) : null;
  const time = hasTimeFields ? timePattern(options) : null;
  if ((hasDateFields && date === null) || (hasTimeFields && time === null)) {
    return null;
  }
  return joined(date, time);
}

/** A Georgian date formatter, or null for options it does not cover. */
export function georgianDateFormat(options: Intl.DateTimeFormatOptions = {}): GeorgianDateFormat | null {
  const pattern = patternOf(options);
  if (pattern === null) {
    return null;
  }
  const fields = fieldReader(options.timeZone);
  const format = (date: Date): string => pattern(fields(date));
  const isMediumDate = options.dateStyle === "medium" && options.timeStyle === undefined;
  return {
    format,
    formatRange(from, to) {
      const [start, end] = [fields(from), fields(to)];
      const [startText, endText] = [pattern(start), pattern(end)];
      if (startText === endText) {
        return startText;
      }
      // "2–20 ოქტ. 2026", "2 სექ. – 1 ოქტ. 2026": the shared year is written once.
      if (isMediumDate && start.year === end.year) {
        const endPart = `${end.day} ${MONTHS_SHORT[end.month - 1]}. ${end.year}`;
        return start.month === end.month
          ? `${start.day}–${endPart}`
          : `${start.day} ${MONTHS_SHORT[start.month - 1]}. – ${endPart}`;
      }
      return `${startText} – ${endText}`;
    },
  };
}

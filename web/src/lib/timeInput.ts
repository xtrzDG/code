/**
 * Times of day as a form edits them: the value is "HH:MM" on a 24-hour
 * clock whatever the cabinet's language; people read and type it in the
 * locale's clock ("08:30" in Russian and Georgian, "8:30 AM" in English).
 *
 * `parseTypedTime` understands what people type: "0830", "830", "8:30",
 * "08.30", "8", "20:30", "8:30 pm", "8p" and the locale's own AM/PM.
 */

import { dateTimeFormat } from "./intl/formatters";
import { dayPeriods, hourCycle } from "./intl/localeCalendar";

export const MINUTES_PER_DAY = 24 * 60;

const TIME_VALUE = /^([01]\d|2[0-3]):([0-5]\d)$/;

/** "08:30" -> 510; null for anything that is not a 24-hour "HH:MM". */
export function minutesOf(value: string): number | null {
  const match = TIME_VALUE.exec(value);
  return match ? Number(match[1]) * 60 + Number(match[2]) : null;
}

/** 510 -> "08:30" (wrapped into one day: 1440 -> "00:00", -15 -> "23:45"). */
export function timeValue(minutes: number): string {
  const wrapped = ((Math.round(minutes) % MINUTES_PER_DAY) + MINUTES_PER_DAY) % MINUTES_PER_DAY;
  return `${String(Math.floor(wrapped / 60)).padStart(2, "0")}:${String(wrapped % 60).padStart(2, "0")}`;
}

/**
 * One arrow press: to the next (or previous) multiple of `step` minutes,
 * so 08:10 goes up to 08:15 and down to 08:00; past midnight it wraps.
 */
export function stepTime(minutes: number, direction: 1 | -1, step: number): number {
  const size = Math.max(1, Math.round(step));
  const onGrid = minutes % size === 0;
  const next =
    direction === 1
      ? onGrid
        ? minutes + size
        : Math.ceil(minutes / size) * size
      : onGrid
        ? minutes - size
        : Math.floor(minutes / size) * size;
  return ((next % MINUTES_PER_DAY) + MINUTES_PER_DAY) % MINUTES_PER_DAY;
}

/** A time as the locale reads it: 510 -> "08:30" (ru, ka), "8:30 AM" (en). */
export function timeText(minutes: number, locale: string): string {
  const cycle = hourCycle(locale);
  const date = new Date(Date.UTC(2024, 0, 1, 0, ((minutes % MINUTES_PER_DAY) + MINUTES_PER_DAY) % MINUTES_PER_DAY));
  return dateTimeFormat(locale, {
    hour: cycle === "h12" ? "numeric" : "2-digit",
    minute: "2-digit",
    hourCycle: cycle,
    timeZone: "UTC",
  }).format(date);
}

/** A typed day period, or null: "pm", "p", "p.m." and the locale's own names. */
function periodOf(text: string, locale: string): "am" | "pm" | null {
  const word = text.replace(/[.\s]/g, "").toLowerCase();
  if (word === "") {
    return null;
  }
  const { am, pm } = dayPeriods(locale);
  const own = (name: string) => name.replace(/[.\s]/g, "").toLowerCase();
  if (word === "a" || word === "am" || word === own(am)) {
    return "am";
  }
  if (word === "p" || word === "pm" || word === own(pm)) {
    return "pm";
  }
  return null;
}

/**
 * A time typed by a person as minutes after midnight, or null. Digits are
 * read on a 24-hour clock ("2030" is 20:30) unless a day period follows
 * ("830 pm"), which needs an hour from 1 to 12.
 */
export function parseTypedTime(text: string, locale: string): number | null {
  const trimmed = text.trim();
  const match = /^(\d{1,2})(?:\s*[:.h\s]\s*(\d{2}))?\s*(\D*)$/i.exec(trimmed) ?? /^(\d{1,2})(\d{2})\s*(\D*)$/.exec(trimmed);
  if (!match) {
    return null;
  }
  const hour = Number(match[1]);
  const minute = match[2] === undefined ? 0 : Number(match[2]);
  const rest = (match[3] ?? "").trim();
  if (minute > 59) {
    return null;
  }
  if (rest === "") {
    return hour <= 23 ? hour * 60 + minute : null;
  }
  const period = periodOf(rest, locale);
  if (period === null || hour < 1 || hour > 12) {
    return null;
  }
  return ((hour % 12) + (period === "pm" ? 12 : 0)) * 60 + minute;
}

/** Whether the locale reads a 12-hour clock (an AM/PM part after the minutes). */
export function isTwelveHour(locale: string): boolean {
  return hourCycle(locale) === "h12";
}


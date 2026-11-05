/**
 * The hosted chat page's "open now" line and weekly hours: the business's
 * opening intervals (ISO weekdays, minutes of the local day, an evening
 * past midnight split at 24:00 into the next weekday) read against the
 * business's own clock, wherever the visitor is.
 */

import type { OpeningInterval } from "@/api/types";

import { MINUTES_PER_DAY, WEEKDAYS, intervalsToWeek, isRoundTheClock } from "../hours";
import { formatMinutesOfDay } from "../format";
import { calendarParts } from "../intl/calendarFields";

/** The business's wall clock: ISO weekday (1 = Monday) and minute of the day. */
export interface BusinessClock {
  weekday: number;
  minute: number;
}

export type OpenState =
  /** Open every minute of every day. */
  | { kind: "always" }
  /** Open now; `closesAt` is the local "HH:MM" it closes at. */
  | { kind: "open"; closesAt: string }
  /** Closed now; opens in `inDays` days (0 today) at `opensAt` on `weekday`. */
  | { kind: "closed"; opensAt: string; inDays: number; weekday: number }
  /** No hours at all. */
  | { kind: "unknown" };

export interface WeekRow {
  weekday: number;
  /** "10:00–23:00", "18:00–02:00"; empty when closed all day. */
  ranges: string[];
  isAllDay: boolean;
  isToday: boolean;
}

interface Range {
  start: number;
  end: number;
}

const DAYS_AHEAD = 8;
const CLOCK_FIELDS: Intl.DateTimeFormatOptions = { weekday: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23" };
const SHORT_WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/** The wall clock of `timeZone` at `now` (an unknown zone reads as UTC). */
export function businessClock(now: Date, timeZone: string): BusinessClock {
  let parts: Partial<Record<Intl.DateTimeFormatPartTypes, string>>;
  try {
    parts = calendarParts(now, timeZone, CLOCK_FIELDS);
  } catch {
    parts = calendarParts(now, "UTC", CLOCK_FIELDS);
  }
  const weekday = SHORT_WEEKDAYS.indexOf(parts.weekday ?? "") + 1;
  return { weekday: weekday || 1, minute: Number(parts.hour ?? 0) * 60 + Number(parts.minute ?? 0) };
}

/**
 * The opening ranges from yesterday to a week ahead, in minutes from today's
 * local midnight, touching ranges joined (Fri 18:00–24:00 + Sat 00:00–02:00).
 */
function rangesAround(intervals: readonly OpeningInterval[], today: number): Range[] {
  const ranges: Range[] = [];
  for (let offset = -1; offset <= DAYS_AHEAD; offset += 1) {
    const weekday = ((((today - 1 + offset) % 7) + 7) % 7) + 1;
    for (const interval of intervals) {
      if (interval.weekday !== weekday) {
        continue;
      }
      const closes = interval.closes_at <= interval.opens_at ? interval.closes_at + MINUTES_PER_DAY : interval.closes_at;
      ranges.push({ start: offset * MINUTES_PER_DAY + interval.opens_at, end: offset * MINUTES_PER_DAY + closes });
    }
  }
  ranges.sort((left, right) => left.start - right.start);
  const joined: Range[] = [];
  for (const range of ranges) {
    const last = joined[joined.length - 1];
    if (last && range.start <= last.end) {
      last.end = Math.max(last.end, range.end);
    } else {
      joined.push({ ...range });
    }
  }
  return joined;
}

function clockText(minutes: number): string {
  return formatMinutesOfDay(((minutes % MINUTES_PER_DAY) + MINUTES_PER_DAY) % MINUTES_PER_DAY);
}

/** Whether the business is open at `clock`, and when that changes. */
export function openState(intervals: readonly OpeningInterval[], clock: BusinessClock): OpenState {
  if (intervals.length === 0) {
    return { kind: "unknown" };
  }
  const ranges = rangesAround(intervals, clock.weekday);
  const current = ranges.find((range) => range.start <= clock.minute && clock.minute < range.end);
  if (current) {
    const whole = -MINUTES_PER_DAY >= current.start && current.end >= (DAYS_AHEAD + 1) * MINUTES_PER_DAY;
    return whole ? { kind: "always" } : { kind: "open", closesAt: clockText(current.end) };
  }
  const next = ranges.find((range) => range.start > clock.minute);
  if (!next) {
    return { kind: "unknown" };
  }
  const inDays = Math.floor(next.start / MINUTES_PER_DAY);
  return {
    kind: "closed",
    opensAt: clockText(next.start),
    inDays,
    weekday: ((clock.weekday - 1 + inDays) % 7) + 1,
  };
}

/** Monday to Sunday as the owner entered them, today marked. */
export function weekRows(intervals: readonly OpeningInterval[], today: number): WeekRow[] {
  const week = intervalsToWeek(intervals);
  return WEEKDAYS.map((weekday) => {
    const day = week.find((entry) => entry.weekday === weekday);
    const pieces = day?.intervals ?? [];
    return {
      weekday,
      isAllDay: pieces.some(isRoundTheClock),
      ranges: pieces
        .filter((piece) => !isRoundTheClock(piece))
        .map((piece) => `${formatMinutesOfDay(piece.opens)}–${formatMinutesOfDay(piece.closes)}`),
      isToday: weekday === today,
    };
  });
}

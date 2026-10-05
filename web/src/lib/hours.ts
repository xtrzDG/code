/**
 * Opening hours between the API and the weekly editor.
 *
 * The API keeps every interval inside one local day: minutes 0..1439 to
 * 1..1440 (1440 = midnight at the end of the day), and hours past midnight
 * as a second interval on the next weekday (Fri 18:00–24:00 + Sat 00:00–02:00).
 *
 * The editor shows what owners think in: "Fri 18:00–02:00". There a closing
 * time at or before the opening time means "the next day", and 00:00 as the
 * closing time means midnight.
 */

import type { OpeningInterval, Weekday } from "@/api/types";

export const WEEKDAYS: readonly Weekday[] = [1, 2, 3, 4, 5, 6, 7];

export const MINUTES_PER_DAY = 1440;

/** One editor row: `closes` is 0..1439; `closes <= opens` runs past midnight. */
export interface EditorInterval {
  opens: number;
  closes: number;
}

export interface DayHours {
  weekday: Weekday;
  intervals: EditorInterval[];
}

function nextWeekday(weekday: Weekday): Weekday {
  return (weekday === 7 ? 1 : weekday + 1) as Weekday;
}

/** True when an editor interval ends on the next day (not at midnight). */
export function isOvernight(interval: EditorInterval): boolean {
  return interval.closes !== 0 && interval.closes <= interval.opens;
}

/** True for 00:00–00:00: open the whole day. */
export function isRoundTheClock(interval: EditorInterval): boolean {
  return interval.opens === 0 && interval.closes === 0;
}

/** API intervals -> one editor entry per weekday, overnight pieces joined. */
export function intervalsToWeek(intervals: readonly OpeningInterval[]): DayHours[] {
  const byDay = new Map<Weekday, { opens: number; closes: number; consumed: boolean }[]>(
    WEEKDAYS.map((weekday) => [weekday, []]),
  );
  for (const interval of intervals) {
    byDay.get(interval.weekday)?.push({ opens: interval.opens_at, closes: interval.closes_at, consumed: false });
  }
  for (const list of byDay.values()) {
    list.sort((left, right) => left.opens - right.opens);
  }

  // A piece 00:00–HH:MM continues the previous day's interval that ends at 24:00.
  const continuation = new Map<Weekday, number>();
  for (const weekday of WEEKDAYS) {
    const today = byDay.get(weekday) ?? [];
    const last = today[today.length - 1];
    const tomorrow = byDay.get(nextWeekday(weekday)) ?? [];
    const first = tomorrow[0];
    if (
      last &&
      first &&
      last.closes === MINUTES_PER_DAY &&
      last.opens > 0 &&
      first.opens === 0 &&
      first.closes < MINUTES_PER_DAY &&
      !first.consumed
    ) {
      first.consumed = true;
      continuation.set(weekday, first.closes);
    }
  }

  return WEEKDAYS.map((weekday) => {
    const pieces = byDay.get(weekday) ?? [];
    const editor: EditorInterval[] = [];
    pieces.forEach((piece, index) => {
      if (piece.consumed) {
        return;
      }
      const isLast = index === pieces.length - 1;
      const carried = isLast ? continuation.get(weekday) : undefined;
      if (carried !== undefined) {
        editor.push({ opens: piece.opens, closes: carried });
      } else {
        editor.push({ opens: piece.opens, closes: piece.closes === MINUTES_PER_DAY ? 0 : piece.closes });
      }
    });
    return { weekday, intervals: editor };
  });
}

/** Editor week -> API intervals (overnight rows split at midnight), sorted. */
export function weekToIntervals(week: readonly DayHours[]): OpeningInterval[] {
  const intervals: OpeningInterval[] = [];
  for (const day of week) {
    for (const interval of day.intervals) {
      if (isRoundTheClock(interval) || interval.closes === 0) {
        intervals.push({ weekday: day.weekday, opens_at: interval.opens, closes_at: MINUTES_PER_DAY });
      } else if (isOvernight(interval)) {
        intervals.push({ weekday: day.weekday, opens_at: interval.opens, closes_at: MINUTES_PER_DAY });
        intervals.push({ weekday: nextWeekday(day.weekday), opens_at: 0, closes_at: interval.closes });
      } else {
        intervals.push({ weekday: day.weekday, opens_at: interval.opens, closes_at: interval.closes });
      }
    }
  }
  return intervals.sort((left, right) => left.weekday - right.weekday || left.opens_at - right.opens_at);
}

/**
 * Weekdays whose API intervals overlap (the API refuses those); useful to
 * point at the day before saving.
 */
export function overlappingWeekdays(intervals: readonly OpeningInterval[]): Weekday[] {
  const result: Weekday[] = [];
  for (const weekday of WEEKDAYS) {
    const day = intervals
      .filter((interval) => interval.weekday === weekday)
      .sort((left, right) => left.opens_at - right.opens_at);
    if (day.some((interval, index) => index > 0 && interval.opens_at < (day[index - 1]?.closes_at ?? 0))) {
      result.push(weekday);
    }
  }
  return result;
}

/**
 * The segments of a time field (hours, minutes and, on a 12-hour clock,
 * AM/PM) and what a key does to them. Pure, so the field's behaviour is
 * tested without a browser:
 *
 * - digits fill the hours, then move on: "0830" is 08:30, "2030" is 20:30
 *   (on a 12-hour clock too: 8:30 PM), a first digit above 2 is a whole
 *   hour ("9" goes on to the minutes), "25" is 2 and the 5 starts the minutes;
 * - ":" or "." moves to the minutes, "a" / "p" (or the locale's own names)
 *   choose AM or PM from any segment;
 * - arrows step the hours by one, the minutes by `step` along its grid
 *   (carrying into the hours) and flip AM and PM.
 */

import type { DayPeriods, HourCycle } from "./intl/localeCalendar";
import { MINUTES_PER_DAY, minutesOf, stepTime, timeValue } from "./timeInput";

export type TimeSegment = "hour" | "minute" | "period";

export type DayPeriod = "am" | "pm";

/** What the field holds, complete or not; `hour` is 0–23. */
export interface TimeDraft {
  hour: number | null;
  minute: number | null;
  /** A chosen half of the day while the hour is still empty (12-hour clock). */
  period: DayPeriod | null;
}

/** The field's state between two keys: the draft, the focused segment and the digits typed into it so far. */
export interface TimeEditing {
  draft: TimeDraft;
  segment: TimeSegment;
  buffer: string;
}

export const EMPTY_DRAFT: TimeDraft = { hour: null, minute: null, period: null };

export function segmentsOf(cycle: HourCycle): TimeSegment[] {
  return cycle === "h12" ? ["hour", "minute", "period"] : ["hour", "minute"];
}

export function draftFromValue(value: string): TimeDraft {
  const minutes = minutesOf(value);
  return minutes === null ? EMPTY_DRAFT : { hour: Math.floor(minutes / 60), minute: minutes % 60, period: null };
}

/** "HH:MM" when hours and minutes are both there, else "". */
export function draftValue(draft: TimeDraft): string {
  return draft.hour === null || draft.minute === null ? "" : timeValue(draft.hour * 60 + draft.minute);
}

export function periodOfDraft(draft: TimeDraft): DayPeriod | null {
  return draft.hour === null ? draft.period : draft.hour >= 12 ? "pm" : "am";
}

/** The hour as shown: "08" on a 24-hour clock, "08" for 8 AM and 8 PM on a 12-hour one ("12" for midnight and noon). */
export function hourText(hour: number, cycle: HourCycle): string {
  const shown = cycle === "h12" ? hour % 12 || 12 : hour;
  return String(shown).padStart(2, "0");
}

/**
 * An hour typed as a number (0–23) into the draft. On a 12-hour clock 0 is
 * midnight, 13–23 are afternoon hours, and 1–12 keep the half of the day
 * already chosen (morning when none is).
 */
function withTypedHour(draft: TimeDraft, typed: number, cycle: HourCycle): TimeDraft {
  if (cycle === "h23" || typed === 0 || typed >= 13) {
    return { ...draft, hour: typed, period: null };
  }
  const period = periodOfDraft(draft) ?? "am";
  return { ...draft, hour: (typed % 12) + (period === "pm" ? 12 : 0), period: null };
}

export function withPeriod(draft: TimeDraft, period: DayPeriod): TimeDraft {
  if (draft.hour === null) {
    return { ...draft, period };
  }
  return { ...draft, hour: (draft.hour % 12) + (period === "pm" ? 12 : 0), period: null };
}

function nextSegment(segment: TimeSegment, cycle: HourCycle): TimeSegment {
  const order = segmentsOf(cycle);
  return order[Math.min(order.indexOf(segment) + 1, order.length - 1)] ?? segment;
}

/** "a", "am", "p", the locale's own first letters: the half of the day a key chooses. */
function periodKey(key: string, periods: DayPeriods): DayPeriod | null {
  const letter = key.toLowerCase();
  if (letter === "a" || letter === periods.am.charAt(0).toLowerCase()) {
    return "am";
  }
  if (letter === "p" || letter === periods.pm.charAt(0).toLowerCase()) {
    return "pm";
  }
  return null;
}

function typeHourDigit(state: TimeEditing, digit: number, cycle: HourCycle): TimeEditing {
  if (state.buffer === "") {
    if (digit <= 2) {
      // "1" may become 10–19: wait for the next digit (shown as typed meanwhile).
      return { ...state, draft: digit === 0 && cycle === "h12" ? state.draft : withTypedHour(state.draft, digit, cycle), buffer: String(digit) };
    }
    return { draft: withTypedHour(state.draft, digit, cycle), segment: "minute", buffer: "" };
  }
  const first = Number(state.buffer);
  const both = first * 10 + digit;
  if (both <= 23) {
    return { draft: withTypedHour(state.draft, both, cycle), segment: "minute", buffer: "" };
  }
  // "25": the hour is 2, the 5 starts the minutes.
  const moved: TimeEditing = { draft: withTypedHour(state.draft, first, cycle), segment: "minute", buffer: "" };
  return typeMinuteDigit(moved, digit, cycle);
}

function typeMinuteDigit(state: TimeEditing, digit: number, cycle: HourCycle): TimeEditing {
  if (state.buffer === "") {
    const draft = { ...state.draft, minute: digit };
    return digit <= 5
      ? { ...state, draft, buffer: String(digit) }
      : { draft, segment: nextSegment("minute", cycle), buffer: "" };
  }
  const draft = { ...state.draft, minute: Number(state.buffer) * 10 + digit };
  return { draft, segment: nextSegment("minute", cycle), buffer: "" };
}

/** One typed character in the focused segment. */
export function typeKey(state: TimeEditing, key: string, cycle: HourCycle, periods: DayPeriods): TimeEditing {
  if (/^\d$/.test(key)) {
    const digit = Number(key);
    if (state.segment === "hour") {
      return typeHourDigit(state, digit, cycle);
    }
    if (state.segment === "minute") {
      return typeMinuteDigit(state, digit, cycle);
    }
    return state;
  }
  if (/^[:.\s,h]$/i.test(key)) {
    return state.segment === "period" ? state : { ...state, segment: nextSegment(state.segment, cycle), buffer: "" };
  }
  const period = cycle === "h12" ? periodKey(key, periods) : null;
  if (period !== null) {
    return { draft: withPeriod(state.draft, period), segment: state.segment, buffer: "" };
  }
  return state;
}

/** Several characters at once (a paste, a browser filling the field): one after another. */
export function typeText(state: TimeEditing, text: string, cycle: HourCycle, periods: DayPeriods): TimeEditing {
  return [...text].reduce((current, key) => typeKey(current, key, cycle, periods), state);
}

/**
 * An arrow press on a segment. An empty field starts from `fallback`
 * ("09:00"); the minutes step along their `step` grid and carry into the
 * hours; the hours wrap around the day.
 */
export function stepSegment(
  draft: TimeDraft,
  segment: TimeSegment,
  direction: 1 | -1,
  options: { step: number; fallback: number },
): TimeDraft {
  if (segment === "period") {
    const current = periodOfDraft(draft) ?? "am";
    return withPeriod(draft, current === "am" ? "pm" : "am");
  }
  if (draft.hour === null && draft.minute === null) {
    return { hour: Math.floor(options.fallback / 60), minute: options.fallback % 60, period: null };
  }
  if (segment === "hour") {
    const hour = draft.hour === null ? Math.floor(options.fallback / 60) : (draft.hour + direction + 24) % 24;
    return { ...draft, hour, period: null };
  }
  if (draft.minute === null) {
    return { ...draft, minute: 0 };
  }
  if (draft.hour === null) {
    return { ...draft, minute: stepTime(draft.minute, direction, options.step) % 60 };
  }
  const total = stepTime(draft.hour * 60 + draft.minute, direction, options.step) % MINUTES_PER_DAY;
  return { hour: Math.floor(total / 60), minute: total % 60, period: null };
}

/** Backspace or Delete on a segment: it empties (AM/PM stays: an hour always has one). */
export function clearSegment(draft: TimeDraft, segment: TimeSegment): TimeDraft {
  if (segment === "hour") {
    return { ...draft, hour: null, period: periodOfDraft(draft) };
  }
  if (segment === "minute") {
    return { ...draft, minute: null };
  }
  return draft;
}

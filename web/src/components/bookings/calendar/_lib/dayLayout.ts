/**
 * The day grid's geometry: where a booking sits on one local day (minutes
 * from that day's midnight, cut to the day), the hours the grid shows,
 * side-by-side lanes for bookings that overlap on one place (three tables
 * of a terrace), and how full each place is.
 */

import type { BookingView } from "@/components/insights/types";
import { parseTimeOfDay } from "@/lib/format";

import type { GridOpenRange, GridPlaceDay } from "./calendarTypes";

export const MINUTES_PER_DAY = 1440;
/** Bookings move and start in steps of a quarter of an hour. */
export const SLOT_MINUTES = 15;
/** The hours shown on a day with nothing open and nothing booked. */
const QUIET_DAY = { start: 9 * 60, end: 18 * 60 } as const;

/** Minutes from the local day's midnight, [start, end). */
export interface Span {
  start: number;
  end: number;
}

/** "HH:MM" -> minutes; "24:00" (an end at midnight) -> 1440. */
export function minuteOfTime(time: string | null | undefined): number | null {
  if (!time) {
    return null;
  }
  return time === "24:00" ? MINUTES_PER_DAY : parseTimeOfDay(time);
}

/**
 * The part of a time-slot booking on `date`: one that began the day before
 * starts at midnight, one that ends the next day runs to the end; null when
 * none of it is on that day, or for a stay (it has no time).
 */
export function daySpan(booking: Pick<BookingView, "date" | "time" | "end_date" | "end_time">, date: string): Span | null {
  const startMinute = minuteOfTime(booking.time);
  if (startMinute === null || booking.date > date || booking.end_date < date) {
    return null;
  }
  const start = booking.date < date ? 0 : startMinute;
  const endMinute = minuteOfTime(booking.end_time);
  const end = booking.end_date > date ? MINUTES_PER_DAY : (endMinute ?? Math.min(start + 60, MINUTES_PER_DAY));
  return end > start ? { start, end } : null;
}

/** The hours the grid shows: every opening and booking of the day, to whole hours. */
export function timeAxis(ranges: readonly GridOpenRange[], spans: readonly Span[]): Span {
  const starts = [...ranges.map((range) => range.opens_at), ...spans.map((span) => span.start)];
  const ends = [...ranges.map((range) => range.closes_at), ...spans.map((span) => span.end)];
  if (starts.length === 0) {
    return { ...QUIET_DAY };
  }
  const start = Math.floor(Math.min(...starts) / 60) * 60;
  const end = Math.min(Math.ceil(Math.max(...ends) / 60) * 60, MINUTES_PER_DAY);
  return { start, end: Math.max(end, start + 60) };
}

export interface Laned<Item> {
  item: Item;
  span: Span;
  /** Its lane among the bookings it overlaps, from 0. */
  lane: number;
  /** How many lanes that group of overlapping bookings needs. */
  lanes: number;
}

/**
 * Lanes for overlapping bookings: each takes the first lane free at its
 * start; a group of bookings that overlap one another (directly or through
 * a third) shares one lane count, so their widths match.
 */
export function layoutLanes<Item>(entries: readonly { item: Item; span: Span }[]): Laned<Item>[] {
  const sorted = [...entries].sort((a, b) => a.span.start - b.span.start || b.span.end - a.span.end);
  const placed: Laned<Item>[] = [];
  let group: Laned<Item>[] = [];
  let laneEnds: number[] = [];
  let groupEnd = -1;
  const closeGroup = () => {
    for (const entry of group) {
      entry.lanes = laneEnds.length;
    }
    group = [];
    laneEnds = [];
  };
  for (const entry of sorted) {
    if (entry.span.start >= groupEnd) {
      closeGroup();
    }
    const free = laneEnds.findIndex((end) => end <= entry.span.start);
    const lane = free === -1 ? laneEnds.length : free;
    laneEnds[lane] = entry.span.end;
    groupEnd = Math.max(groupEnd, entry.span.end);
    const laned = { ...entry, lane, lanes: 1 };
    group.push(laned);
    placed.push(laned);
  }
  closeGroup();
  return placed;
}

/** A minute rounded to the nearest step (15 minutes). */
export function snapMinutes(minutes: number, step: number = SLOT_MINUTES): number {
  return Math.round(minutes / step) * step;
}

/** A start kept inside the grid's hours so the whole booking shows (or at least its first step). */
export function clampStart(start: number, duration: number, axis: Span): number {
  const latest = Math.max(axis.start, axis.end - Math.min(duration, axis.end - axis.start));
  return Math.min(Math.max(start, axis.start), latest);
}

/** "HH:MM" of a minute of the day. */
export function timeOfMinute(minutes: number): string {
  const clamped = Math.min(Math.max(minutes, 0), MINUTES_PER_DAY - SLOT_MINUTES);
  return `${String(Math.floor(clamped / 60)).padStart(2, "0")}:${String(clamped % 60).padStart(2, "0")}`;
}

/**
 * How full a place is on the day, from the bookings shown: unit-minutes its
 * bookings fill within its opening ranges, over what its units could fill.
 * Computed here so a booking moved a moment ago counts at once.
 */
export function placeLoad(placeDay: GridPlaceDay, spans: readonly Span[]): { share: number | null; count: number } {
  const open = placeDay.open_unit_minutes ?? 0;
  if (!placeDay.is_open || open === 0) {
    return { share: null, count: spans.length };
  }
  let booked = 0;
  for (const span of spans) {
    for (const range of placeDay.open_ranges ?? []) {
      booked += Math.max(Math.min(span.end, range.closes_at) - Math.max(span.start, range.opens_at), 0);
    }
  }
  return { share: Math.min(booked / open, 1), count: spans.length };
}

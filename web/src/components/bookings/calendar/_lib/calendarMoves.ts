/**
 * Moving a booking on the calendar: the booking as it will look once moved
 * (shown at once, before the API answers), the reschedule body with the
 * start the calendar showed (the API refuses when someone moved it since),
 * the move back for Undo, and the keyboard's steps.
 */

import { addDays, daysBetween } from "@/components/insights/dates";
import type { BookingView, RescheduleBookingBody } from "@/components/insights/types";

import type { MoveTarget } from "./calendarTypes";
import { minuteOfTime, MINUTES_PER_DAY, SLOT_MINUTES, timeOfMinute } from "./dayLayout";

/** Minutes from the start of `origin` to `date` `time`. */
function minutesFrom(origin: string, date: string, time: string | null | undefined): number {
  return daysBetween(origin, date) * MINUTES_PER_DAY + (minuteOfTime(time) ?? 0);
}

/** A date and time `minutes` after the start of `origin`. */
function momentAfter(origin: string, minutes: number): { date: string; time: string } {
  const days = Math.floor(minutes / MINUTES_PER_DAY);
  const rest = minutes - days * MINUTES_PER_DAY;
  return { date: addDays(origin, days), time: `${String(Math.floor(rest / 60)).padStart(2, "0")}:${String(rest % 60).padStart(2, "0")}` };
}

/** How long a time-slot booking lasts, in minutes (an hour when the end is unknown). */
export function durationOf(booking: Pick<BookingView, "date" | "time" | "end_date" | "end_time">): number {
  if (!booking.time || !booking.end_time) {
    return 60;
  }
  return Math.max(minutesFrom(booking.date, booking.end_date, booking.end_time) - (minuteOfTime(booking.time) ?? 0), SLOT_MINUTES);
}

/** The booking as the calendar shows it once moved: same length (or nights), the new place and start. */
export function movedView(booking: BookingView, target: MoveTarget): BookingView {
  const place = { resource_id: target.resourceId, resource_name: target.resourceName };
  if (target.time === null || !booking.time) {
    const nights = daysBetween(booking.date, booking.end_date);
    return { ...booking, ...place, date: target.date, end_date: addDays(target.date, nights) };
  }
  const end = momentAfter(target.date, (minuteOfTime(target.time) ?? 0) + durationOf(booking));
  return { ...booking, ...place, date: target.date, time: target.time, end_date: end.date, end_time: end.time };
}

/** Whether the target is where the booking already is. */
export function isSameSpot(booking: BookingView, target: MoveTarget): boolean {
  return booking.resource_id === target.resourceId && booking.date === target.date && (booking.time ?? null) === target.time;
}

/** The reschedule body: the new place and start, and the start the calendar showed. */
export function moveBody(booking: BookingView, target: MoveTarget): RescheduleBookingBody {
  return {
    new_date: target.date,
    new_time: target.time,
    new_resource_id: target.resourceId,
    expected_date: booking.date,
    expected_time: booking.time ?? null,
  };
}

/** Where Undo puts a moved booking back: its place and start before the move. */
export function placeOf(booking: BookingView): MoveTarget {
  return { resourceId: booking.resource_id, resourceName: booking.resource_name, date: booking.date, time: booking.time ?? null };
}

/** A place of the calendar in its order (a column of the day, a row of the nights). */
export interface MovePlace {
  id: string;
  name: string;
}

/**
 * The keyboard's next target: Up/Down move a time-slot booking a quarter of
 * an hour (a stay moves between rooms), the side arrows move it to the
 * place beside (a stay a night earlier or later), within the grid's bounds.
 * `forward` is the arrow pointing to the next column in reading order.
 */
export function keyboardTarget(
  current: MoveTarget,
  key: string,
  places: readonly MovePlace[],
  bounds: { firstMinute: number; lastMinute: number; firstDate: string; lastDate: string },
  forward: "ArrowRight" | "ArrowLeft",
): MoveTarget | null {
  const backward = forward === "ArrowRight" ? "ArrowLeft" : "ArrowRight";
  const index = places.findIndex((place) => place.id === current.resourceId);
  const placeAt = (step: number): MoveTarget | null => {
    const next = places[index + step];
    return next ? { ...current, resourceId: next.id, resourceName: next.name } : null;
  };
  if (current.time === null) {
    const dateAt = (step: number): MoveTarget | null => {
      const date = addDays(current.date, step);
      return date < bounds.firstDate || date > bounds.lastDate ? null : { ...current, date };
    };
    const moves: Record<string, () => MoveTarget | null> = {
      ArrowUp: () => placeAt(-1),
      ArrowDown: () => placeAt(1),
      [forward]: () => dateAt(1),
      [backward]: () => dateAt(-1),
    };
    return moves[key]?.() ?? null;
  }
  const minute = minuteOfTime(current.time) ?? 0;
  const timeAt = (step: number): MoveTarget | null => {
    const next = minute + step * SLOT_MINUTES;
    return next < bounds.firstMinute || next > bounds.lastMinute ? null : { ...current, time: timeOfMinute(next) };
  };
  const moves: Record<string, () => MoveTarget | null> = {
    ArrowUp: () => timeAt(-1),
    ArrowDown: () => timeAt(1),
    [forward]: () => placeAt(1),
    [backward]: () => placeAt(-1),
  };
  return moves[key]?.() ?? null;
}

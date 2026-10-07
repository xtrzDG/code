/**
 * Where a booking dragged on the day grid would land: the place column
 * under (or nearest to) the pointer, and the start its top edge would have,
 * to a quarter of an hour, kept inside the grid's hours.
 */

import type { PointerEvent } from "react";

import type { BookingView } from "@/components/insights/types";

import { durationOf } from "../_lib/calendarMoves";
import { clampStart, snapMinutes, timeOfMinute, type Span } from "../_lib/dayLayout";
import type { Locate } from "../useMoveGestures";

/** One hour of the day grid is this tall (px); a quarter of an hour, 14 px. */
export const HOUR_HEIGHT = 56;
export const MINUTE_HEIGHT = HOUR_HEIGHT / 60;

interface Column {
  id: string;
  name: string;
  rect: DOMRect;
}

/** The place column under `x`, or the nearest one (a pointer past the last column). */
function columnAt(container: HTMLElement | null, x: number): Column | null {
  let nearest: Column | null = null;
  let nearestDistance = Number.POSITIVE_INFINITY;
  for (const element of container?.querySelectorAll<HTMLElement>("[data-calendar-column]") ?? []) {
    const rect = element.getBoundingClientRect();
    const distance = x < rect.left ? rect.left - x : x > rect.right ? x - rect.right : 0;
    if (distance < nearestDistance) {
      nearestDistance = distance;
      nearest = { id: element.dataset.calendarColumn ?? "", name: element.dataset.placeName ?? "", rect };
    }
  }
  return nearest;
}

/** The locator of a booking grabbed on the day grid (the grab point stays under the pointer). */
export function dayLocator(
  container: () => HTMLElement | null,
  booking: BookingView,
  date: string,
  axis: Span,
): (event: PointerEvent<HTMLElement>) => Locate {
  return (event) => {
    const grabY = event.clientY - event.currentTarget.getBoundingClientRect().top;
    const duration = durationOf(booking);
    return (x, y) => {
      const column = columnAt(container(), x);
      if (!column) {
        return null;
      }
      const minute = clampStart(snapMinutes(axis.start + (y - grabY - column.rect.top) / MINUTE_HEIGHT), duration, axis);
      return { resourceId: column.id, resourceName: column.name, date, time: timeOfMinute(minute) };
    };
  };
}

/** The quarter of an hour clicked in a column (rounded down, so the click falls inside it). */
export function minuteAtClick(clientY: number, column: HTMLElement, axis: Span): number {
  const offset = (clientY - column.getBoundingClientRect().top) / MINUTE_HEIGHT;
  return Math.min(Math.max(axis.start + Math.floor(offset / 15) * 15, axis.start), axis.end - 15);
}

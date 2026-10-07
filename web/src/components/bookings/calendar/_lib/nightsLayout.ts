/**
 * The hotel grid (rooms × nights): which nights of the window a stay takes
 * (the night of each date from check-in up to the day before check-out),
 * and lanes so the stays of a room type with several rooms sit one under
 * another.
 */

import { daysBetween } from "@/components/insights/dates";
import type { BookingView } from "@/components/insights/types";

import { layoutLanes, type Laned } from "./dayLayout";

export interface StayNights {
  /** The first night shown, as an index of the window. */
  first: number;
  /** How many nights of the window it takes. */
  count: number;
  /** It began before the window (or ends after it): the bar is cut there. */
  startsBefore: boolean;
  endsAfter: boolean;
}

/** The nights of the window a stay takes (its check-in and check-out times aside); null when none. */
export function stayNights(booking: Pick<BookingView, "date" | "end_date">, from: string, days: number): StayNights | null {
  const start = daysBetween(from, booking.date);
  const end = daysBetween(from, booking.end_date);
  const first = Math.max(start, 0);
  const last = Math.min(end, days);
  if (last <= first) {
    return null;
  }
  return { first, count: last - first, startsBefore: start < 0, endsAfter: end > days };
}

/** Stays of one room type in lanes (at least as many as it has rooms, so the rows keep their height). */
export function layoutStays<Item>(entries: readonly { item: Item; nights: StayNights }[], rooms: number): { stays: Laned<Item>[]; lanes: number } {
  const stays = layoutLanes(entries.map(({ item, nights }) => ({ item, span: { start: nights.first, end: nights.first + nights.count } })));
  const lanes = Math.max(rooms, 1, ...stays.map((stay) => stay.lane + 1));
  return { stays, lanes };
}

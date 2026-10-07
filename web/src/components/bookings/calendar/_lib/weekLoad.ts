/**
 * The week's heatmap: how full a place is on a day (unit-minutes for time
 * slots, rooms for nights), in five steps of colour, and the whole
 * business's day in one figure.
 */

import type { CalendarDay, GridPlaceDay } from "./calendarTypes";

/** Steps of the heatmap: 0 nothing booked … 4 nearly full. */
export type LoadLevel = 0 | 1 | 2 | 3 | 4;

/** The share of a place's day that is booked; null when it is closed (nothing to fill). */
export function placeDayShare(placeDay: GridPlaceDay): number | null {
  if (placeDay.open_units !== null && placeDay.open_units !== undefined) {
    return placeDay.open_units === 0 ? null : Math.min((placeDay.booked_units ?? 0) / placeDay.open_units, 1);
  }
  const open = placeDay.open_unit_minutes ?? 0;
  return open === 0 ? null : Math.min((placeDay.booked_unit_minutes ?? 0) / open, 1);
}

export function loadLevel(share: number | null): LoadLevel {
  if (share === null || share <= 0) {
    return 0;
  }
  if (share < 0.25) {
    return 1;
  }
  if (share < 0.5) {
    return 2;
  }
  return share < 0.8 ? 3 : 4;
}

/** How much of the accent a level mixes into the surface (text stays AA on every step). */
export const LEVEL_MIX: Record<LoadLevel, number> = { 0: 0, 1: 14, 2: 28, 3: 42, 4: 56 };

/**
 * The business's day: the share of all time-slot places together (by
 * unit-minutes), or of the rooms when it books only nights; null when
 * nothing is open; with every booking of the day.
 */
export function dayLoad(day: Pick<CalendarDay, "places">): { share: number | null; count: number } {
  const count = day.places.reduce((sum, place) => sum + place.booking_count, 0);
  const slots = day.places.filter((place) => (place.open_unit_minutes ?? 0) > 0);
  if (slots.length > 0) {
    const open = slots.reduce((sum, place) => sum + (place.open_unit_minutes ?? 0), 0);
    const booked = slots.reduce((sum, place) => sum + (place.booked_unit_minutes ?? 0), 0);
    return { share: Math.min(booked / open, 1), count };
  }
  const rooms = day.places.filter((place) => (place.open_units ?? 0) > 0);
  if (rooms.length === 0) {
    return { share: null, count };
  }
  const open = rooms.reduce((sum, place) => sum + (place.open_units ?? 0), 0);
  const booked = rooms.reduce((sum, place) => sum + (place.booked_units ?? 0), 0);
  return { share: Math.min(booked / open, 1), count };
}

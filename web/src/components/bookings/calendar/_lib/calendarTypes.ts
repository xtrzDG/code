/**
 * The bookings calendar's API types (GET …/bookings/grid) and its views.
 */

import type { Schema } from "@/api/types";
import type { BookingView } from "@/components/insights/types";

export type BookingGrid = Schema<"BookingGrid">;
export type GridPlace = Schema<"BookingGridPlace">;
export type GridPlaceDay = Schema<"BookingGridPlaceDay">;
type GridDay = Schema<"BookingGridDay">;
export type GridOpenRange = Schema<"GridOpenRange">;

/** A day of the window with its lists filled in (the API leaves empty ones out). */
export interface CalendarDay extends Omit<GridDay, "places" | "business_ranges"> {
  places: GridPlaceDay[];
  business_ranges: GridOpenRange[];
}

/** A window of the calendar with its lists filled in. */
export interface CalendarGrid extends Omit<BookingGrid, "places" | "days" | "bookings"> {
  places: GridPlace[];
  days: CalendarDay[];
  bookings: BookingView[];
}

/** The API's window with every list present, so views never check for a missing one. */
export function filledGrid(grid: BookingGrid): CalendarGrid {
  return {
    ...grid,
    places: grid.places ?? [],
    bookings: grid.bookings ?? [],
    days: (grid.days ?? []).map((day) => ({ ...day, places: day.places ?? [], business_ranges: day.business_ranges ?? [] })),
  };
}

/** Day: places as columns over the hours; Week: the load heatmap; Nights: rooms × nights. */
export type CalendarView = "day" | "week" | "nights";

const CALENDAR_VIEWS: readonly CalendarView[] = ["day", "week", "nights"];

export function isCalendarView(value: string | null | undefined): value is CalendarView {
  return (CALENDAR_VIEWS as readonly string[]).includes(value ?? "");
}

/** Where a dragged (or keyboard-moved) booking would land. */
export interface MoveTarget {
  resourceId: string;
  resourceName: string;
  date: string;
  /** "HH:MM" for a time-slot booking; null for a stay (it keeps its nights). */
  time: string | null;
}

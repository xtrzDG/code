/**
 * The calendar's windows in the shared cache (R1 query cache): a booking
 * changed anywhere (moved on the grid, its status set in its details) is
 * replaced in every window loaded, at once; a cancelled one drops out.
 */

import { queryCache, type Rollback } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import type { BookingView } from "@/components/insights/types";

import type { BookingGrid } from "./_lib/calendarTypes";

/** Every loaded window of the calendar with the booking replaced; returns how to undo it. */
export function replaceInGrids(businessId: string, booking: BookingView): Rollback {
  return queryCache.update<BookingGrid>(queryKeys.bookings.grids(businessId), (grid) =>
    grid.bookings?.some((item) => item.id === booking.id)
      ? { ...grid, bookings: grid.bookings.map((item) => (item.id === booking.id ? booking : item)) }
      : grid,
  );
}

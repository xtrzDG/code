"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";

/**
 * One window of the calendar (GET …/bookings/grid): `days` local days from
 * `from` with every place, its hours and load, and (unless `withBookings`
 * is false: the week's heatmap) the bookings in it. The previous window
 * stays on screen, dimmed, while the next one loads.
 */
export function useBookingGrid(window: { from: string; days: number }, options: { includeTest: boolean; withBookings: boolean }) {
  const { business } = useBusiness();
  const businessId = business.id;
  const key = queryKeys.bookings.grid(businessId, { ...window, ...options });
  return useQuery(
    key,
    () =>
      api.GET("/v1/businesses/{business_id}/bookings/grid", {
        params: {
          path: { business_id: businessId },
          query: {
            date: window.from,
            days: String(window.days),
            include_sandbox: options.includeTest ? "true" : undefined,
            include_bookings: options.withBookings ? undefined : "false",
          },
        },
      }),
    { keepPreviousData: true },
  );
}

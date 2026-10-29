"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useCursorPage } from "@/api/useCursorPage";
import { useBusiness } from "@/components/business/BusinessContext";
import type { BookingPage, BookingView } from "@/components/insights/types";
import { useToday } from "@/components/insights/useToday";

/** A busy day fits one page; more come with "show more". */
const AGENDA_PAGE_SIZE = 100;

/**
 * Today's bookings for the phone's agenda (every place and status, test
 * bookings when the list shows them), kept with the other bookings lists so
 * status changes and live events update both.
 */
export function useTodayBookings({ enabled, includeTest }: { enabled: boolean; includeTest: boolean }) {
  const { business } = useBusiness();
  const today = useToday(business.timezone);
  const key = queryKeys.bookings.list(business.id, {
    range: "agenda",
    from: today,
    to: today,
    status: null,
    resourceId: null,
    includeTest,
  });
  return useCursorPage<BookingView, BookingPage>(
    key,
    ({ cursor, limit }) =>
      api.GET("/v1/businesses/{business_id}/bookings", {
        params: {
          path: { business_id: business.id },
          query: {
            from: today,
            to: today,
            order: "earliest_first",
            ...(includeTest ? { include_sandbox: "true" } : {}),
            limit: String(limit),
            cursor: cursor ?? undefined,
          },
        },
      }),
    { enabled, pageSize: AGENDA_PAGE_SIZE },
  );
}

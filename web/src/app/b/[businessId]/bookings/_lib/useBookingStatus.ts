"use client";

import { api } from "@/api/client";
import type { PagedData } from "@/api/paging";
import { queryCache, type QueryKey } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import type { BookingPage, BookingStatus, BookingView } from "@/components/insights/types";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

type BookingList = PagedData<BookingView, BookingPage>;

/** The cached list with one booking replaced by another copy of it. */
export function withBooking(data: BookingList, booking: BookingView): BookingList {
  return { ...data, items: data.items.map((item) => (item.id === booking.id ? booking : item)) };
}

/**
 * Confirming, completing and marking a no-show: the booking shows its new
 * status at once (in the list and in its open details) and goes back if
 * the API refuses. These moves cannot be reversed by the API (a completed
 * booking stays completed), so no Undo is offered.
 */
export function useBookingStatus(listKey: QueryKey, showDetails: (booking: BookingView) => void) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();

  const mutation = useMutation(
    (booking: BookingView, status: BookingStatus) =>
      api.PATCH("/v1/businesses/{business_id}/bookings/{booking_id}", {
        params: { path: { business_id: business.id, booking_id: booking.id } },
        body: { status },
      }),
    {
      errorMessages: { conflict: "bookings.errors.conflict" },
      optimistic: (booking, status) => {
        showDetails({ ...booking, status });
        return queryCache.update<BookingList>(listKey, (data) => withBooking(data, { ...booking, status }));
      },
      rollback: (_error, booking) => showDetails(booking),
      // Other ranges and filters, free slots and the dashboard follow when shown.
      stale: [queryKeys.bookings.all(business.id), queryKeys.conversations.all(business.id)],
      invalidate: [queryKeys.dashboard.all(business.id)],
    },
  );

  const run = async (booking: BookingView, status: BookingStatus) => {
    const result = await mutation.run(booking, status);
    if (result.ok) {
      queryCache.update<BookingList>(listKey, (data) => withBooking(data, result.data));
      showDetails(result.data);
      toast.success(t("bookings.updated"));
    }
  };

  return { run, isPending: mutation.isPending };
}

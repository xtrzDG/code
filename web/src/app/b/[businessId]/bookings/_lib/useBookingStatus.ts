"use client";

import { api } from "@/api/client";
import type { PagedData } from "@/api/paging";
import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { BOOKING_STATUS } from "@/components/insights/labels";
import type { BookingPage, BookingStatus, BookingView } from "@/components/insights/types";
import { useToast, type ToastTitle } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { UNDO_REFUSAL_MESSAGES } from "./bookingUndo";

type BookingList = PagedData<BookingView, BookingPage>;

/** The cached list with one booking replaced by another copy of it. */
export function withBooking(data: BookingList, booking: BookingView): BookingList {
  return { ...data, items: data.items.map((item) => (item.id === booking.id ? booking : item)) };
}

/** Every loaded bookings list (each range and filter, and today's agenda) with the booking replaced. */
export function replaceInLists(businessId: string, booking: BookingView) {
  return queryCache.update<BookingList>(["bookings", businessId, "list"], (data) => withBooking(data, booking));
}

/**
 * Confirming, completing, marking a no-show (and, through `afterCancel`,
 * cancelling): the booking shows its new status at once, everywhere it is
 * listed and in its open details, and goes back if the API refuses. Each
 * change says so in a toast with Undo, which asks the API to restore the
 * previous status (revert-status); the API refuses with a reason when the
 * freed time was taken in the meantime.
 */
export function useBookingStatus(showDetails: (booking: BookingView) => void) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  // Other ranges and filters, free slots and the dashboard follow when shown.
  const stale = [queryKeys.bookings.all(business.id), queryKeys.conversations.all(business.id)];
  const invalidate = [queryKeys.dashboard.all(business.id)];

  const change = useMutation(
    (booking: BookingView, status: BookingStatus) =>
      api.PATCH("/v1/businesses/{business_id}/bookings/{booking_id}", {
        params: { path: { business_id: business.id, booking_id: booking.id } },
        body: { status },
      }),
    {
      errorMessages: { conflict: "bookings.errors.conflict" },
      optimistic: (booking, status) => {
        showDetails({ ...booking, status });
        return replaceInLists(business.id, { ...booking, status });
      },
      rollback: (_error, booking) => showDetails(booking),
      stale,
      invalidate,
    },
  );

  const revert = useMutation(
    (changed: BookingView, _previous: BookingStatus) =>
      api.POST("/v1/businesses/{business_id}/bookings/{booking_id}/revert-status", {
        params: { path: { business_id: business.id, booking_id: changed.id } },
        body: { status: changed.status },
      }),
    {
      reasonMessages: UNDO_REFUSAL_MESSAGES,
      optimistic: (changed, previous) => {
        showDetails({ ...changed, status: previous });
        return replaceInLists(business.id, { ...changed, status: previous });
      },
      rollback: (_error, changed) => showDetails(changed),
      // A refusal means the booking changed elsewhere: reload the lists on screen.
      invalidate: (data) => (data === undefined ? [...invalidate, ["bookings", business.id, "list"]] : invalidate),
      stale,
    },
  );

  /** Puts back the status a change replaced; true when the API agreed. */
  const undo = async (changed: BookingView, previous: BookingStatus): Promise<boolean> => {
    const result = await revert.run(changed, previous);
    if (result.ok) {
      replaceInLists(business.id, result.data);
      showDetails(result.data);
      toast.success(t("bookings.undo.done", { status: t(BOOKING_STATUS[result.data.status].label) }));
    }
    return result.ok;
  };

  /** Offers Undo for a change the API made (`changed` has the new status). */
  const offerUndo = (message: ToastTitle, changed: BookingView, previous: BookingStatus, onUndone?: () => void) => {
    toast.undoable(message, () => {
      void undo(changed, previous).then((isUndone) => {
        if (isUndone) {
          onUndone?.();
        }
      });
    });
  };

  /** Sets the status; `message` is the toast's text (by default "Booking updated"). */
  const run = async (booking: BookingView, status: BookingStatus, message?: ToastTitle): Promise<boolean> => {
    const result = await change.run(booking, status);
    if (result.ok) {
      replaceInLists(business.id, result.data);
      showDetails(result.data);
      offerUndo(message ?? t("bookings.updated"), result.data, booking.status);
    }
    return result.ok;
  };

  return { run, offerUndo, isPending: change.isPending || revert.isPending };
}

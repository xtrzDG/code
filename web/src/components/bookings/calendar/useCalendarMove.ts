"use client";

import type { ReasonMessages } from "@/api/errors";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { replaceInLists } from "@/app/b/[businessId]/bookings/_lib/useBookingStatus";
import { BOOKING_REFUSAL_MESSAGES } from "@/app/b/[businessId]/bookings/_lib/bookingRefusals";
import { customerLanguage } from "@/app/b/[businessId]/bookings/_lib/bookingList";
import { useBusiness } from "@/components/business/BusinessContext";
import { formatLocalDate, formatLocalTime } from "@/components/insights/dates";
import type { BookingView } from "@/components/insights/types";
import { useToast, type ToastTitle } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { isSameSpot, moveBody, movedView, placeOf } from "./_lib/calendarMoves";
import type { MoveTarget } from "./_lib/calendarTypes";

/** The API's refusals of a move in the user's language (someone moved it since: `booking_changed`). */
const MOVE_REFUSAL_MESSAGES: ReasonMessages = {
  ...BOOKING_REFUSAL_MESSAGES,
  booking_changed: () => ({ key: "bookingCalendar.move.changed" }),
};

/**
 * Moving a booking on the calendar (POST …/reschedule with the place it was
 * dropped on and the start the calendar showed): it shows at its new place
 * at once, everywhere it is listed, and goes back if the API refuses (then
 * the windows on screen load again, as someone else changed it). A toast
 * says where it went, with Undo: the same move back, from where it is now.
 */
export function useCalendarMove() {
  const { t, locale } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const businessId = business.id;

  const reschedule = useMutation(
    (booking: BookingView, target: MoveTarget) =>
      api.POST("/v1/businesses/{business_id}/bookings/{booking_id}/reschedule", {
        params: { path: { business_id: businessId, booking_id: booking.id }, query: { language: customerLanguage(booking, business) } },
        body: moveBody(booking, target),
      }),
    {
      optimistic: (booking, target) => replaceInLists(businessId, movedView(booking, target)),
      errorMessages: { conflict: "bookings.errors.conflict" },
      reasonMessages: MOVE_REFUSAL_MESSAGES,
      // Other windows, the list and free slots follow when next shown.
      stale: [queryKeys.bookings.all(businessId), queryKeys.conversations.all(businessId)],
      invalidate: (data) =>
        data === undefined
          ? [queryKeys.dashboard.all(businessId), queryKeys.bookings.grids(businessId)]
          : [queryKeys.dashboard.all(businessId)],
    },
  );

  const movedTitle = (moved: BookingView, asStay: boolean): ToastTitle =>
    moved.time && !asStay
      ? { text: t("bookingCalendar.move.moved", { time: formatLocalTime(moved.time, locale) }), values: { place: moved.resource_name } }
      : {
          text: t("bookingCalendar.move.movedStay", { date: formatLocalDate(moved.date, locale, { day: "numeric", month: "short" }) }),
          values: { place: moved.resource_name },
        };

  const moveBack = async (moved: BookingView, original: BookingView, asStay: boolean) => {
    const result = await reschedule.run(moved, placeOf(original, asStay));
    if (result.ok) {
      replaceInLists(businessId, result.data.booking);
      toast.success(t("bookingCalendar.move.undone"));
    }
  };

  /** Moves the booking; true once the API agreed. A drop where it already is does nothing. */
  const move = async (booking: BookingView, target: MoveTarget): Promise<boolean> => {
    if (isSameSpot(booking, target)) {
      return false;
    }
    const result = await reschedule.run(booking, target);
    if (!result.ok) {
      return false;
    }
    const moved = result.data.booking;
    replaceInLists(businessId, moved);
    toast.undoable(movedTitle(moved, target.time === null), () => void moveBack(moved, booking, target.time === null));
    return true;
  };

  return { move, isMoving: reschedule.isPending };
}

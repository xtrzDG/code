"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useCursorPage } from "@/api/useCursorPage";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import type { CalendarView } from "@/components/bookings/calendar/_lib/calendarTypes";
import type { CalendarDraft } from "@/components/bookings/calendar/BookingCalendar";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToday } from "@/components/insights/useToday";
import type { BookingPage, BookingView } from "@/components/insights/types";
import { replaceUrlQuery } from "@/components/insights/urlQuery";
import { useI18n } from "@/i18n/client";
import { COMPACT_SCREEN_QUERY, useMediaQuery, WIDE_SCREEN_QUERY } from "@/lib/useMediaQuery";

import { bookingApiQuery, bookingFiltersQuery, isRangeValid, rangeDates, type BookingFilters, type PhoneBookingsView } from "./bookingFilters";
import { customerLanguage, nightsOf } from "./bookingList";
import type { BookingFormValues } from "./manualBooking";
import { replaceInLists, useBookingStatus } from "./useBookingStatus";
import { useTodayBookings } from "./useTodayBookings";

export type BookingDialog =
  | { kind: "none" }
  | { kind: "create"; initial?: Partial<BookingFormValues> }
  | { kind: "details" | "edit" | "reschedule" | "cancel" | "noShow"; booking: BookingView }
  | { kind: "message"; title: string; text: string };

/**
 * The bookings page's state: filters kept in the URL, the paged list (on
 * large screens, and on phones under "All bookings") and today's agenda
 * (phones), places from the API, the open dialog, and changing a booking's
 * status or cancelling it (with the text for the customer), each with Undo.
 */
export function useBookingsPage(initialFilters: BookingFilters) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const businessId = business.id;
  const today = useToday(business.timezone);
  const [filters, setFiltersState] = useState(initialFilters);
  const [dialog, setDialog] = useState<BookingDialog>({ kind: "none" });
  const [cancelLanguage, setCancelLanguage] = useState(business.default_language);
  // False until hydrated, so neither view loads before the screen is known.
  const isCompact = useMediaQuery(COMPACT_SCREEN_QUERY);
  const isWide = useMediaQuery(WIDE_SCREEN_QUERY);

  const range = rangeDates(filters, today);
  const rangeValid = isRangeValid(range);

  const listKey = queryKeys.bookings.list(businessId, {
    ...range,
    range: filters.range,
    status: filters.status,
    resourceId: filters.resourceId,
    includeTest: filters.includeTest,
  });
  const bookings = useCursorPage<BookingView, BookingPage>(
    listKey,
    ({ cursor, limit }) =>
      api.GET("/v1/businesses/{business_id}/bookings", {
        params: {
          path: { business_id: businessId },
          query: { ...bookingApiQuery(filters, range), limit: String(limit), cursor: cursor ?? undefined },
        },
      }),
    { enabled: rangeValid && filters.calendar === null && (isWide || filters.phoneView === "all") },
  );
  const agenda = useTodayBookings({
    enabled: isCompact && filters.calendar === null && filters.phoneView === "today",
    includeTest: filters.includeTest,
  });
  const resources = useQuery(queryKeys.resources.list(businessId), () =>
    api.GET("/v1/businesses/{business_id}/resources", { params: { path: { business_id: businessId } } }),
  );

  // The open details follow a status change (and go back with it).
  const showDetails = (booking: BookingView) =>
    setDialog((current) =>
      "booking" in current && current.booking.id === booking.id && (current.kind === "details" || current.kind === "noShow")
        ? { kind: "details", booking }
        : current,
    );
  const status = useBookingStatus(showDetails);
  const cancel = useMutation(
    (booking: BookingView, language: string) =>
      api.POST("/v1/businesses/{business_id}/bookings/{booking_id}/cancel", {
        params: { path: { business_id: businessId, booking_id: booking.id }, query: { language } },
      }),
    {
      errorMessages: { conflict: "bookings.errors.conflict" },
      stale: [queryKeys.bookings.all(businessId), queryKeys.conversations.all(businessId)],
      invalidate: [queryKeys.dashboard.all(businessId)],
    },
  );

  const setFilters = (next: BookingFilters) => {
    setFiltersState(next);
    replaceUrlQuery(bookingFiltersQuery(next));
  };
  const setPhoneView = (phoneView: PhoneBookingsView) => setFilters({ ...filters, phoneView, calendar: null });
  /** Opens the calendar (a view, a date, test bookings or not); `view: null` goes back to the list. */
  const showCalendar = (change: { view?: CalendarView | null; anchor?: string; includeTest?: boolean }) =>
    setFilters({
      ...filters,
      calendar: change.view === undefined ? filters.calendar : change.view,
      date: change.anchor ?? filters.date,
      includeTest: change.includeTest ?? filters.includeTest,
    });
  /** A new booking started on the calendar: its date, time and place filled in. */
  const createAt = (draft: CalendarDraft) =>
    setDialog({ kind: "create", initial: { date: draft.date, time: draft.time ?? "", resourceId: draft.resourceId } });

  const replaceBooking = (updated: BookingView) => replaceInLists(businessId, updated);

  const resourceUnits = new Map((resources.data?.items ?? []).map((resource) => [resource.id, resource.booking_unit]));
  const isStay = (booking: BookingView) =>
    resourceUnits.get(booking.resource_id) === "night" || (booking.time === null && nightsOf(booking) > 0);

  // Modal also reports a close when another dialog replaces it: only close the current one.
  const closeIf = (kind: BookingDialog["kind"]) => () =>
    setDialog((current) => (current.kind === kind ? { kind: "none" } : current));

  const runCancel = async (booking: BookingView) => {
    const result = await cancel.run(booking, cancelLanguage);
    if (result.ok) {
      replaceBooking(result.data.booking);
      // Undone, the cancellation's text for the customer has nothing left to say.
      status.offerUndo(t("bookings.cancelled"), result.data.booking, booking.status, closeIf("message"));
      setDialog({ kind: "message", title: t("bookings.cancelled"), text: result.data.confirmation_text });
    }
  };

  const openCancel = (booking: BookingView) => {
    setCancelLanguage(customerLanguage(booking, business));
    setDialog({ kind: "cancel", booking });
  };
  const close = () => setDialog({ kind: "none" });
  const dialogBooking = "booking" in dialog ? dialog.booking : null;
  const defaultDate = range.from && range.from > today ? range.from : today;

  return {
    isCompact,
    filters,
    setFilters,
    setPhoneView,
    showCalendar,
    createAt,
    range,
    rangeValid,
    today,
    defaultDate,
    bookings,
    agenda,
    resources: resources.data?.items ?? [],
    dialog,
    setDialog,
    dialogBooking,
    close,
    closeIf,
    isStay,
    replaceBooking,
    runStatus: status.run,
    isChangingStatus: status.isPending,
    cancelLanguage,
    setCancelLanguage,
    openCancel,
    runCancel,
    isCancelling: cancel.isPending,
  };
}

export type BookingsPage = ReturnType<typeof useBookingsPage>;

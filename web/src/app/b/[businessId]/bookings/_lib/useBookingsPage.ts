"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToday } from "@/components/insights/useToday";
import type { BookingPage, BookingStatus, BookingView } from "@/components/insights/types";
import { replaceUrlQuery } from "@/components/insights/urlQuery";
import { usePagedQuery } from "@/components/insights/usePagedQuery";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { bookingApiQuery, bookingFiltersQuery, isRangeValid, rangeDates, type BookingFilters } from "./bookingFilters";
import { customerLanguage, nightsOf } from "./bookingList";


export type BookingDialog =
  | { kind: "none" }
  | { kind: "create" }
  | { kind: "details" | "edit" | "reschedule" | "cancel" | "noShow"; booking: BookingView }
  | { kind: "message"; title: string; text: string };

/**
 * The bookings page's state: filters kept in the URL, the paged list and
 * places from the API, the open dialog, and changing a booking's status or
 * cancelling it (with the text for the customer).
 */
export function useBookingsPage(initialFilters: BookingFilters) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const businessId = business.id;
  const today = useToday(business.timezone);
  const [filters, setFiltersState] = useState(initialFilters);
  const [dialog, setDialog] = useState<BookingDialog>({ kind: "none" });
  const [cancelLanguage, setCancelLanguage] = useState(business.default_language);

  const range = rangeDates(filters, today);
  const rangeValid = isRangeValid(range);

  const bookings = usePagedQuery<BookingView, BookingPage>(
    ({ cursor, limit }) =>
      api.GET("/v1/businesses/{business_id}/bookings", {
        params: {
          path: { business_id: businessId },
          query: { ...bookingApiQuery(filters, range), limit: String(limit), cursor: cursor ?? undefined },
        },
      }),
    [businessId, range.from, range.to, filters.status, filters.resourceId, filters.includeTest, filters.range],
    { enabled: rangeValid },
  );
  const resources = useApiQuery(
    () => api.GET("/v1/businesses/{business_id}/resources", { params: { path: { business_id: businessId } } }),
    [businessId],
  );

  const changeStatus = useApiMutation(
    (booking: BookingView, status: BookingStatus) =>
      api.PATCH("/v1/businesses/{business_id}/bookings/{booking_id}", {
        params: { path: { business_id: businessId, booking_id: booking.id } },
        body: { status },
      }),
    { errorMessages: { conflict: "bookings.errors.conflict" } },
  );
  const cancel = useApiMutation(
    (booking: BookingView, language: string) =>
      api.POST("/v1/businesses/{business_id}/bookings/{booking_id}/cancel", {
        params: { path: { business_id: businessId, booking_id: booking.id }, query: { language } },
      }),
    { errorMessages: { conflict: "bookings.errors.conflict" } },
  );

  const setFilters = (next: BookingFilters) => {
    setFiltersState(next);
    replaceUrlQuery(bookingFiltersQuery(next));
  };

  const replaceBooking = (updated: BookingView) =>
    bookings.updateItems((items) => items.map((item) => (item.id === updated.id ? updated : item)));

  const resourceUnits = new Map((resources.data?.items ?? []).map((resource) => [resource.id, resource.booking_unit]));
  const isStay = (booking: BookingView) =>
    resourceUnits.get(booking.resource_id) === "night" || (booking.time === null && nightsOf(booking) > 0);

  const runStatus = async (booking: BookingView, status: BookingStatus) => {
    const result = await changeStatus.run(booking, status);
    if (result.ok) {
      replaceBooking(result.data);
      toast.success(t("bookings.updated"));
      setDialog({ kind: "details", booking: result.data });
    }
  };

  const runCancel = async (booking: BookingView) => {
    const result = await cancel.run(booking, cancelLanguage);
    if (result.ok) {
      replaceBooking(result.data.booking);
      toast.success(t("bookings.cancelled"));
      setDialog({ kind: "message", title: t("bookings.cancelled"), text: result.data.confirmation_text });
    }
  };

  const openCancel = (booking: BookingView) => {
    setCancelLanguage(customerLanguage(booking, business));
    setDialog({ kind: "cancel", booking });
  };
  const close = () => setDialog({ kind: "none" });
  // Modal also reports a close when another dialog replaces it: only close the current one.
  const closeIf = (kind: BookingDialog["kind"]) => () =>
    setDialog((current) => (current.kind === kind ? { kind: "none" } : current));
  const dialogBooking = "booking" in dialog ? dialog.booking : null;
  const defaultDate = range.from && range.from > today ? range.from : today;

  return {
    filters,
    setFilters,
    range,
    rangeValid,
    today,
    defaultDate,
    bookings,
    resources: resources.data?.items ?? [],
    dialog,
    setDialog,
    dialogBooking,
    close,
    closeIf,
    isStay,
    replaceBooking,
    runStatus,
    isChangingStatus: changeStatus.isPending,
    cancelLanguage,
    setCancelLanguage,
    openCancel,
    runCancel,
    isCancelling: cancel.isPending,
  };
}

export type BookingsPage = ReturnType<typeof useBookingsPage>;

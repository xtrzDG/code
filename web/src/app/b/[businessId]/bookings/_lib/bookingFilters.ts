/**
 * Filters of the bookings page: date ranges in the business time zone, the
 * filters kept in the URL and the list query sent to the API. On phones the
 * page opens on today's agenda unless the address asks for the list (a
 * filter, or `view=all`); `view` only matters there.
 */

import { addDays, isLocalDate, type LocalDateText } from "@/components/insights/dates";
import { BOOKING_STATUSES } from "@/components/insights/labels";
import type { BookingStatus } from "@/components/insights/types";

export const BOOKING_RANGES = ["upcoming", "today", "tomorrow", "week", "past", "custom"] as const;
export type BookingRange = (typeof BOOKING_RANGES)[number];

/** What a phone shows: today's agenda or the filtered list. */
export type PhoneBookingsView = "today" | "all";

export interface BookingFilters {
  phoneView: PhoneBookingsView;
  range: BookingRange;
  /** Only for the custom range. */
  from: LocalDateText | null;
  to: LocalDateText | null;
  status: BookingStatus | null;
  resourceId: string | null;
  includeTest: boolean;
}

export const DEFAULT_BOOKING_FILTERS: BookingFilters = {
  phoneView: "today",
  range: "upcoming",
  from: null,
  to: null,
  status: null,
  resourceId: null,
  includeTest: false,
};

type SearchParams = Record<string, string | string[] | undefined>;

function single(params: SearchParams, key: string): string | null {
  const value = params[key];
  return typeof value === "string" ? value : null;
}

/** Filters from the page URL (`?range=custom&from=2026-10-01&to=2026-10-07&status=confirmed`). */
export function parseBookingFilters(params: SearchParams): BookingFilters {
  const range = single(params, "range");
  const status = single(params, "status");
  const from = single(params, "from");
  const to = single(params, "to");
  const filters: Omit<BookingFilters, "phoneView"> = {
    range: (BOOKING_RANGES as readonly string[]).includes(range ?? "") ? (range as BookingRange) : "upcoming",
    from: from && isLocalDate(from) ? from : null,
    to: to && isLocalDate(to) ? to : null,
    status: (BOOKING_STATUSES as readonly string[]).includes(status ?? "") ? (status as BookingStatus) : null,
    resourceId: single(params, "resource"),
    includeTest: single(params, "test") === "1",
  };
  const view = single(params, "view");
  const phoneView: PhoneBookingsView =
    view === "today" || view === "all" ? view : hasListFilters(filters) ? "all" : "today";
  return { phoneView, ...filters };
}

/** Whether anything but the defaults is chosen for the list (a phone then opens on it). */
function hasListFilters(filters: Omit<BookingFilters, "phoneView">): boolean {
  return (
    filters.range !== "upcoming" ||
    filters.status !== null ||
    filters.resourceId !== null ||
    filters.includeTest
  );
}

/** The filters of the phone's sheet that differ from their defaults (status, place, test bookings). */
export function sheetFilterCount(filters: BookingFilters): number {
  return [filters.status !== null, filters.resourceId !== null, filters.includeTest].filter(Boolean).length;
}

/** The sheet's filters back to their defaults; the dates stay. */
export function withoutSheetFilters(filters: BookingFilters): BookingFilters {
  return { ...filters, status: null, resourceId: null, includeTest: false };
}

export function bookingFiltersQuery(filters: BookingFilters): string {
  const params = new URLSearchParams();
  if (filters.range !== "upcoming") params.set("range", filters.range);
  if (filters.range === "custom" && filters.from) params.set("from", filters.from);
  if (filters.range === "custom" && filters.to) params.set("to", filters.to);
  if (filters.status) params.set("status", filters.status);
  if (filters.resourceId) params.set("resource", filters.resourceId);
  if (filters.includeTest) params.set("test", "1");
  const impliedView: PhoneBookingsView = hasListFilters(filters) ? "all" : "today";
  if (filters.phoneView !== impliedView) params.set("view", filters.phoneView);
  return params.toString();
}

/** The API's inclusive `from`/`to` local dates for the chosen range (null = open end). */
export function rangeDates(
  filters: Pick<BookingFilters, "range" | "from" | "to">,
  today: LocalDateText,
): { from: LocalDateText | null; to: LocalDateText | null } {
  switch (filters.range) {
    case "today":
      return { from: today, to: today };
    case "tomorrow":
      return { from: addDays(today, 1), to: addDays(today, 1) };
    case "week":
      return { from: today, to: addDays(today, 6) };
    case "past":
      return { from: addDays(today, -30), to: addDays(today, -1) };
    case "custom":
      return { from: filters.from, to: filters.to };
    default:
      return { from: today, to: null };
  }
}

/** The API query of the list filters (past ranges read latest first). */
export function bookingApiQuery(
  filters: BookingFilters,
  range: { from: LocalDateText | null; to: LocalDateText | null },
): {
  from?: LocalDateText;
  to?: LocalDateText;
  status?: BookingStatus;
  resource_id?: string;
  include_sandbox?: "true";
  order: "earliest_first" | "latest_first";
} {
  return {
    ...(range.from ? { from: range.from } : {}),
    ...(range.to ? { to: range.to } : {}),
    ...(filters.status ? { status: filters.status } : {}),
    ...(filters.resourceId ? { resource_id: filters.resourceId } : {}),
    ...(filters.includeTest ? { include_sandbox: "true" as const } : {}),
    order: filters.range === "past" ? "latest_first" : "earliest_first",
  };
}

export function isRangeValid(range: { from: LocalDateText | null; to: LocalDateText | null }): boolean {
  return range.from === null || range.to === null || range.from <= range.to;
}

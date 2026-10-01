/**
 * Pure rules of the bookings page: date ranges in the business time zone,
 * URL filters, grouping by day, allowed actions and the manual booking form.
 */

import { z } from "zod";

import { addDays, daysBetween, isLocalDate, isLocalTime, type LocalDateText } from "@/components/insights/dates";
import { BOOKING_STATUSES } from "@/components/insights/labels";
import type {
  AvailableSlot,
  BookingStatus,
  BookingUnit,
  BookingUpdateBody,
  BookingView,
  ChannelKind,
  ManualBookingBody,
  ResourceView,
} from "@/components/insights/types";
import type { MessageKey } from "@/i18n/translate";
import { fieldErrors, messageKey } from "@/lib/validation";

export const BOOKING_RANGES = ["upcoming", "today", "tomorrow", "week", "past", "custom"] as const;
export type BookingRange = (typeof BOOKING_RANGES)[number];

export interface BookingFilters {
  range: BookingRange;
  /** Only for the custom range. */
  from: LocalDateText | null;
  to: LocalDateText | null;
  status: BookingStatus | null;
  resourceId: string | null;
  includeTest: boolean;
}

export const DEFAULT_BOOKING_FILTERS: BookingFilters = {
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
  return {
    range: (BOOKING_RANGES as readonly string[]).includes(range ?? "") ? (range as BookingRange) : "upcoming",
    from: from && isLocalDate(from) ? from : null,
    to: to && isLocalDate(to) ? to : null,
    status: (BOOKING_STATUSES as readonly string[]).includes(status ?? "") ? (status as BookingStatus) : null,
    resourceId: single(params, "resource"),
    includeTest: single(params, "test") === "1",
  };
}

export function bookingFiltersQuery(filters: BookingFilters): string {
  const params = new URLSearchParams();
  if (filters.range !== "upcoming") params.set("range", filters.range);
  if (filters.range === "custom" && filters.from) params.set("from", filters.from);
  if (filters.range === "custom" && filters.to) params.set("to", filters.to);
  if (filters.status) params.set("status", filters.status);
  if (filters.resourceId) params.set("resource", filters.resourceId);
  if (filters.includeTest) params.set("test", "1");
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

export interface BookingDay {
  date: LocalDateText;
  bookings: BookingView[];
}

/** Bookings by local day; days and times ascending (newest day first for past ranges). */
export function groupBookingsByDate(bookings: readonly BookingView[], options: { newestFirst?: boolean } = {}): BookingDay[] {
  const sorted = [...bookings].sort(
    (left, right) => left.date.localeCompare(right.date) || (left.time ?? "").localeCompare(right.time ?? ""),
  );
  const days: BookingDay[] = [];
  for (const booking of sorted) {
    const last = days.at(-1);
    if (last && last.date === booking.date) {
      last.bookings.push(booking);
    } else {
      days.push({ date: booking.date, bookings: [booking] });
    }
  }
  return options.newestFirst ? days.reverse() : days;
}

export interface BookingActions {
  confirm: boolean;
  complete: boolean;
  noShow: boolean;
  reschedule: boolean;
  cancel: boolean;
}

/**
 * What staff may do with a booking (backend UpdateBookingUseCase:
 * completed, no-show and cancelled from pending or confirmed; confirm from
 * pending). Finished bookings are read-only.
 */
export function bookingActions(status: BookingStatus): BookingActions {
  const active = status === "pending" || status === "confirmed";
  return {
    confirm: status === "pending",
    complete: active,
    noShow: active,
    reschedule: active,
    cancel: active,
  };
}

/** Nights of a stay (0 for a time slot ending the same day). */
export function nightsOf(booking: Pick<BookingView, "date" | "end_date">): number {
  return Math.max(0, daysBetween(booking.date, booking.end_date));
}

/** How a booking is made: the chosen resource's unit, else nights only when every resource is booked by nights. */
export function bookingUnitFor(resources: readonly Pick<ResourceView, "id" | "booking_unit" | "is_active">[], resourceId: string): BookingUnit {
  const chosen = resources.find((resource) => resource.id === resourceId);
  if (chosen) {
    return chosen.booking_unit;
  }
  const active = resources.filter((resource) => resource.is_active);
  return active.length > 0 && active.every((resource) => resource.booking_unit === "night") ? "night" : "time_slot";
}

export interface BookingFormValues {
  contactName: string;
  phone: string;
  date: string;
  time: string;
  nights: string;
  partySize: string;
  resourceId: string;
  notes: string;
  source: ChannelKind;
  language: string;
  /** Country the phone is read in when typed without a country code. */
  country: string;
}

const wholeNumber = (min: number, max: number, message: MessageKey) =>
  z
    .string()
    .trim()
    .regex(/^\d+$/, message)
    .transform(Number)
    .pipe(z.number().int().min(min, message).max(max, message));

const baseSchema = z.object({
  contactName: z.string().trim().min(1, messageKey("bookings.errors.nameRequired")).max(200, messageKey("validation.tooLong")),
  phone: z.string().trim().max(40, messageKey("validation.tooLong")),
  date: z.string().refine(isLocalDate, messageKey("bookings.errors.dateRequired")),
  partySize: wholeNumber(1, 10_000, messageKey("bookings.errors.partySize")),
  notes: z.string().trim().max(1000, messageKey("validation.tooLong")),
});

const timeSchema = z.object({ time: z.string().refine(isLocalTime, messageKey("bookings.errors.timeRequired")) });
const nightsSchema = z.object({ nights: wholeNumber(1, 365, messageKey("bookings.errors.nights")) });

export type BookingFormErrors = Partial<Record<keyof BookingFormValues, MessageKey>>;

/** The POST body of a manual booking, or the field errors (message keys). */
export function validateBookingForm(
  values: BookingFormValues,
  unit: BookingUnit,
): { ok: true; body: ManualBookingBody } | { ok: false; errors: BookingFormErrors } {
  const base = baseSchema.safeParse(values);
  const timing = unit === "night" ? nightsSchema.safeParse(values) : timeSchema.safeParse(values);
  if (!base.success || !timing.success) {
    return {
      ok: false,
      errors: { ...fieldErrors(base), ...fieldErrors(timing as z.ZodSafeParseResult<unknown>) } as BookingFormErrors,
    };
  }
  return {
    ok: true,
    body: {
      contact_name: base.data.contactName,
      contact_phone_number: base.data.phone || null,
      resource_id: values.resourceId || null,
      date: base.data.date,
      time: unit === "night" ? null : values.time,
      nights: unit === "night" && "nights" in timing.data ? timing.data.nights : null,
      party_size: base.data.partySize,
      notes: base.data.notes || null,
      source_channel: values.source,
      language: values.language || null,
      country_hint: values.country || null,
    },
  };
}

export interface ResourceSlots {
  resourceId: string;
  resourceName: string;
  slots: AvailableSlot[];
}

/** Slots grouped by place, in the order the places first appear (best fit first). */
export function groupSlotsByResource(slots: readonly AvailableSlot[]): ResourceSlots[] {
  const groups = new Map<string, ResourceSlots>();
  for (const slot of slots) {
    const group = groups.get(slot.resource_id) ?? { resourceId: slot.resource_id, resourceName: slot.resource_name, slots: [] };
    group.slots.push(slot);
    groups.set(slot.resource_id, group);
  }
  return [...groups.values()];
}

/** The customer's language for texts about a booking: theirs when the business speaks it. */
export function customerLanguage(
  booking: Pick<BookingView, "language">,
  business: { languages: readonly string[]; default_language: string },
): string {
  return booking.language && business.languages.includes(booking.language) ? booking.language : business.default_language;
}

export type ReminderState = "sent" | "pending" | "none";

/**
 * The customer's reminder: sent (when), still to come for an upcoming
 * active booking, or none (finished, cancelled or already started).
 */
export function reminderState(
  booking: Pick<BookingView, "reminder_sent_at" | "status" | "date">,
  today: LocalDateText,
): ReminderState {
  if (booking.reminder_sent_at) {
    return "sent";
  }
  const isActive = booking.status === "pending" || booking.status === "confirmed";
  return isActive && booking.date >= today ? "pending" : "none";
}

export interface BookingEditValues {
  contactName: string;
  partySize: string;
  resourceId: string;
  notes: string;
}

export type BookingEditErrors = Partial<Record<keyof BookingEditValues, MessageKey>>;

export function bookingEditValues(booking: BookingView): BookingEditValues {
  return {
    contactName: booking.contact_name ?? "",
    partySize: String(booking.party_size),
    resourceId: booking.resource_id,
    notes: booking.notes ?? "",
  };
}

/** Upcoming bookings can change place and party size; finished ones only notes and the name. */
export function canChangePlacement(status: BookingStatus): boolean {
  return status === "pending" || status === "confirmed";
}

/** Places a booking may move to: active ones booked the same way (time slots or nights). */
export function placesForEdit(
  resources: readonly Pick<ResourceView, "id" | "booking_unit" | "is_active" | "name">[],
  booking: Pick<BookingView, "resource_id">,
): Pick<ResourceView, "id" | "booking_unit" | "is_active" | "name">[] {
  const current = resources.find((resource) => resource.id === booking.resource_id);
  return resources.filter(
    (resource) =>
      resource.id === booking.resource_id ||
      (resource.is_active && (!current || resource.booking_unit === current.booking_unit)),
  );
}

const editSchema = z.object({
  contactName: z.string().trim().max(200, messageKey("validation.tooLong")),
  partySize: wholeNumber(1, 10_000, messageKey("bookings.errors.partySize")),
  notes: z.string().trim().max(1000, messageKey("validation.tooLong")),
});

/**
 * The PATCH body with only the changed fields (null when nothing changed),
 * or the field errors. An emptied note is sent as "" (removes it); a name
 * cannot be emptied once set.
 */
export function validateBookingEdit(
  values: BookingEditValues,
  booking: BookingView,
): { ok: true; body: BookingUpdateBody | null } | { ok: false; errors: BookingEditErrors } {
  const parsed = editSchema.safeParse(values);
  if (!parsed.success) {
    return { ok: false, errors: fieldErrors(parsed) as BookingEditErrors };
  }
  if (booking.contact_name && parsed.data.contactName === "") {
    return { ok: false, errors: { contactName: "bookings.errors.nameRequired" } };
  }
  const body: BookingUpdateBody = {};
  if (parsed.data.contactName !== "" && parsed.data.contactName !== (booking.contact_name ?? "")) {
    body.contact_name = parsed.data.contactName;
  }
  if (parsed.data.partySize !== booking.party_size) {
    body.party_size = parsed.data.partySize;
  }
  if (values.resourceId && values.resourceId !== booking.resource_id) {
    body.resource_id = values.resourceId;
  }
  if (parsed.data.notes !== (booking.notes ?? "")) {
    body.notes = parsed.data.notes;
  }
  return { ok: true, body: Object.keys(body).length > 0 ? body : null };
}

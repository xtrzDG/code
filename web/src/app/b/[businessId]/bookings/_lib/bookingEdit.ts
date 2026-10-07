/** Editing a booking: the form values, the places it may move to and the PATCH body. */

import { z } from "@/lib/zod";

import type { BookingStatus, BookingUpdateBody, BookingView, ResourceView } from "@/components/insights/types";
import type { MessageKey } from "@/i18n/translate";
import { fieldErrors, messageKey } from "@/lib/validation";

import { wholeNumber } from "./manualBooking";

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

/**
 * Places a booking may move to: active ones booked the same way (time
 * slots or nights) and, for a booking of a service, only those that
 * perform it (`performerIds`; null when it books no service).
 */
export function placesForEdit(
  resources: readonly Pick<ResourceView, "id" | "booking_unit" | "is_active" | "name">[],
  booking: Pick<BookingView, "resource_id">,
  performerIds: readonly string[] | null = null,
): Pick<ResourceView, "id" | "booking_unit" | "is_active" | "name">[] {
  const current = resources.find((resource) => resource.id === booking.resource_id);
  return resources.filter(
    (resource) =>
      resource.id === booking.resource_id ||
      (resource.is_active &&
        (!current || resource.booking_unit === current.booking_unit) &&
        (performerIds === null || performerIds.includes(resource.id))),
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

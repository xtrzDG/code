/**
 * The manual booking form: how a place is booked (time slots or nights),
 * validation into the POST body, and free slots grouped by place. A
 * booking may name a service, package or room type: it sets the unit
 * (a room type is booked by the night) and the usual length.
 */

import { z } from "@/lib/zod";

import { isLocalDate, isLocalTime } from "@/components/insights/dates";
import type { AvailableSlot, BookingUnit, ChannelKind, ManualBookingBody, ResourceView } from "@/components/insights/types";
import type { MessageKey } from "@/i18n/translate";
import { offerBookingUnit, type OfferItem } from "@/lib/offers";
import { fieldErrors, messageKey } from "@/lib/validation";

/**
 * How a booking is made: the chosen offer's unit, else the chosen
 * resource's, else nights only when every resource is booked by nights.
 */
export function bookingUnitFor(
  resources: readonly Pick<ResourceView, "id" | "booking_unit" | "is_active">[],
  resourceId: string,
  offer: Pick<OfferItem, "kind"> | null = null,
): BookingUnit {
  if (offer) {
    return offerBookingUnit(offer.kind);
  }
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
  /** The service, package or room type booked; "" for none. */
  serviceId: string;
  /** A service's length in minutes, as typed (its usual length at first). */
  duration: string;
  notes: string;
  source: ChannelKind;
  language: string;
  /** Country the phone is read in when typed without a country code. */
  country: string;
}

export const wholeNumber = (min: number, max: number, message: MessageKey) =>
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
const durationSchema = z.object({ duration: wholeNumber(5, 43_200, messageKey("bookings.errors.duration")) });

export type BookingFormErrors = Partial<Record<keyof BookingFormValues, MessageKey>>;

/**
 * The minutes to send for a service: none unless staff typed another
 * length than its usual one (the API books its usual length by itself).
 */
function durationOverride(values: BookingFormValues, unit: BookingUnit, offer: Pick<OfferItem, "duration_minutes"> | null): number | null {
  const typed = values.duration.trim();
  if (!values.serviceId || unit === "night" || typed === "") {
    return null;
  }
  return Number(typed) === (offer?.duration_minutes ?? null) ? null : Number(typed);
}

/** The POST body of a manual booking, or the field errors (message keys). */
export function validateBookingForm(
  values: BookingFormValues,
  unit: BookingUnit,
  offer: Pick<OfferItem, "duration_minutes"> | null = null,
): { ok: true; body: ManualBookingBody } | { ok: false; errors: BookingFormErrors } {
  const base = baseSchema.safeParse(values);
  const timing = unit === "night" ? nightsSchema.safeParse(values) : timeSchema.safeParse(values);
  const checksDuration = Boolean(values.serviceId) && unit === "time_slot" && values.duration.trim() !== "";
  const duration = checksDuration ? durationSchema.safeParse(values) : null;
  if (!base.success || !timing.success || (duration && !duration.success)) {
    return {
      ok: false,
      errors: {
        ...fieldErrors(base),
        ...fieldErrors(timing as z.ZodSafeParseResult<unknown>),
        ...(duration ? fieldErrors(duration as z.ZodSafeParseResult<unknown>) : {}),
      } as BookingFormErrors,
    };
  }
  return {
    ok: true,
    body: {
      contact_name: base.data.contactName,
      contact_phone_number: base.data.phone || null,
      resource_id: values.resourceId || null,
      service_item_id: values.serviceId || null,
      duration_minutes: durationOverride(values, unit, offer),
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

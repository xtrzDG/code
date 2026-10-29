/**
 * The service picker of the manual booking form: which places a chosen
 * offer can be booked at, what choosing it fills in, and how the picker
 * is labelled. Value and performer rules live in lib/offers.ts.
 */

import type { ResourceView } from "@/components/insights/types";
import { offerOfBooking, performersOf, type OfferItem } from "@/lib/offers";

import type { BookingFormValues } from "./manualBooking";

/** The places offered for the booking: the offer's performers, else every active place. */
export function placesForOffer<R extends ResourceView>(
  offer: OfferItem | null,
  resources: readonly R[],
  offers: readonly OfferItem[],
): R[] {
  const active = resources.filter((resource) => resource.is_active);
  return offer ? performersOf(offer, resources, offers) : active;
}

/**
 * The form after choosing an offer (or none): its usual length, and the
 * place kept only while it still performs the offer.
 */
export function withOffer(
  values: BookingFormValues,
  offer: OfferItem | null,
  resources: readonly ResourceView[],
  offers: readonly OfferItem[],
): BookingFormValues {
  const places = placesForOffer(offer, resources, offers);
  const keepsPlace = values.resourceId === "" || places.some((resource) => resource.id === values.resourceId);
  return {
    ...values,
    serviceId: offer?.id ?? "",
    duration: offer?.duration_minutes ? String(offer.duration_minutes) : "",
    resourceId: keepsPlace ? values.resourceId : "",
  };
}

/** "roomType" when every offer is a room type (a hotel picks a type), else "service". */
export function offerPickerKind(offers: readonly Pick<OfferItem, "kind">[]): "roomType" | "service" {
  return offers.length > 0 && offers.every((offer) => offer.kind === "room_type") ? "roomType" : "service";
}

/** The offer the form books: the chosen one, else the chosen room's room type (it values the stay). */
export function bookedOffer<T extends OfferItem>(
  values: Pick<BookingFormValues, "serviceId" | "resourceId">,
  resources: readonly ResourceView[],
  offers: readonly T[],
): T | null {
  const resource = resources.find((item) => item.id === values.resourceId) ?? null;
  return offerOfBooking(values.serviceId || null, resource, offers);
}

/**
 * Bookable offers (services, packages, room types) and the resources that
 * perform or provide them, as the cabinet shows and books them.
 *
 * The rules mirror the API (app/utilities/bookings/bookable_offers.py):
 * a resource performs an offer when either side names the other (the
 * offer's `performer_resource_ids`, the resource's `serves_item_ids`, a
 * room's `room_type_item_id`). An offer nobody is linked to falls to the
 * resources linked to no offer (generalists), else to every active
 * resource booked the same way. A booking of a service is worth its price;
 * a stay is worth its nights, each at the rate of its season.
 */

import type { KnowledgeItemDetails, KnowledgeItemKind, ResourceKind, Schema } from "@/api/types";

export type SeasonalNightlyRate = Schema<"SeasonalNightlyRate">;
type BookingUnit = Schema<"BookingUnit">;

/** What the cabinet needs of a bookable knowledge item. */
export type OfferItem = Pick<KnowledgeItemDetails, "id" | "kind" | "title" | "is_active"> &
  Partial<
    Pick<
      KnowledgeItemDetails,
      "price_minor" | "currency_code" | "duration_minutes" | "buffer_minutes" | "performer_resource_ids" | "seasonal_rates"
    >
  >;

/** What the cabinet needs of a resource to link and filter it. */
export interface OfferResource {
  id: string;
  name: string;
  kind: ResourceKind;
  booking_unit: BookingUnit;
  is_active: boolean;
  serves_item_ids?: string[];
  room_type_item_id?: string | null;
}

/** Kinds a customer books, in the order the API lists them. */
export const BOOKABLE_KINDS: readonly KnowledgeItemKind[] = ["service", "room_type", "package"];

export function isBookableKind(kind: KnowledgeItemKind): boolean {
  return BOOKABLE_KINDS.includes(kind);
}

/** Services and packages block their performer for a break afterwards; a room type has check-out times instead. */
export function kindHasBuffer(kind: KnowledgeItemKind): boolean {
  return kind === "service" || kind === "package";
}

/** Room types are booked by the night, services and packages by time. */
export function offerBookingUnit(kind: KnowledgeItemKind): BookingUnit {
  return kind === "room_type" ? "night" : "time_slot";
}

/** Whether the owner linked the resource and the offer (from either side). */
export function isLinked(item: Pick<OfferItem, "id" | "performer_resource_ids">, resource: OfferResource): boolean {
  return (
    (item.performer_resource_ids ?? []).includes(resource.id) ||
    (resource.serves_item_ids ?? []).includes(item.id) ||
    resource.room_type_item_id === item.id
  );
}

/**
 * The active resources that perform or provide an offer: the linked ones,
 * else the generalists, else every active resource booked the offer's way.
 */
export function performersOf<R extends OfferResource>(item: OfferItem, resources: readonly R[], items: readonly OfferItem[]): R[] {
  const unit = offerBookingUnit(item.kind);
  const active = resources.filter((resource) => resource.is_active && resource.booking_unit === unit);
  const linked = active.filter((resource) => isLinked(item, resource));
  if (linked.length > 0 || resources.some((resource) => isLinked(item, resource))) {
    return linked;
  }
  const offers = items.filter((other) => isBookableKind(other.kind));
  const generalists = active.filter((resource) => !offers.some((offer) => isLinked(offer, resource)));
  return generalists.length > 0 ? generalists : active;
}

/** The names of the resources linked to an offer, in the order of `resources`. */
export function linkedResourceNames(item: OfferItem, resources: readonly OfferResource[]): string[] {
  return resources.filter((resource) => isLinked(item, resource)).map((resource) => resource.name);
}

/** The services and packages a resource is linked to (room types are a room's type, not its services). */
export function servicesOf<T extends OfferItem>(resource: OfferResource, items: readonly T[]): T[] {
  return items.filter((item) => kindHasBuffer(item.kind) && isLinked(item, resource));
}

/** The booked offer: the service asked for, else the room type of the booked room. */
export function offerOfBooking<T extends OfferItem>(
  serviceId: string | null,
  resource: Pick<OfferResource, "room_type_item_id"> | null,
  items: readonly T[],
): T | null {
  if (serviceId) {
    return items.find((item) => item.id === serviceId) ?? null;
  }
  const roomTypeId = resource?.room_type_item_id;
  return roomTypeId ? (items.find((item) => item.id === roomTypeId && item.is_active) ?? null) : null;
}

/** Active offers by kind (in API order) and then by title in the UI language. */
export function sortOffers<T extends OfferItem>(items: readonly T[], locale: string): T[] {
  return items
    .filter((item) => item.is_active && isBookableKind(item.kind))
    .sort(
      (left, right) =>
        BOOKABLE_KINDS.indexOf(left.kind) - BOOKABLE_KINDS.indexOf(right.kind) ||
        left.title.localeCompare(right.title, locale, { sensitivity: "base" }),
    );
}

// --- Value -------------------------------------------------------------------------

/** "MM-DD" of a business-local "YYYY-MM-DD". */
function monthDay(localDate: string): string {
  return localDate.slice(5, 10);
}

/** Whether a night (its "YYYY-MM-DD") falls into a season; a season may run over New Year. */
export function isInSeason(localDate: string, season: Pick<SeasonalNightlyRate, "starts_on" | "ends_on">): boolean {
  const day = monthDay(localDate);
  return season.starts_on <= season.ends_on
    ? season.starts_on <= day && day <= season.ends_on
    : day >= season.starts_on || day <= season.ends_on;
}

/** "YYYY-MM-DD" plus whole days. */
export function addDays(localDate: string, days: number): string {
  const [year, month, day] = localDate.split("-").map(Number);
  const date = new Date(Date.UTC(year ?? 1970, (month ?? 1) - 1, (day ?? 1) + days));
  return date.toISOString().slice(0, 10);
}

/** The rate of the night starting on `localDate`: its season's, else the item's price; null without either. */
export function nightRate(item: Pick<OfferItem, "price_minor" | "seasonal_rates">, localDate: string): number | null {
  const season = (item.seasonal_rates ?? []).find((candidate) => isInSeason(localDate, candidate));
  if (season) {
    return season.nightly_rate_minor;
  }
  return item.price_minor ?? null;
}

/** What `nights` nights from `checkIn` cost, night by night; null when a night has no rate. */
export function stayValueMinor(item: Pick<OfferItem, "price_minor" | "seasonal_rates">, checkIn: string, nights: number): number | null {
  let total = 0;
  for (let night = 0; night < nights; night += 1) {
    const rate = nightRate(item, addDays(checkIn, night));
    if (rate === null) {
      return null;
    }
    total += rate;
  }
  return total;
}

export interface BookingValue {
  minor: number;
  currency: string;
}

/**
 * What a booking of `offer` is worth: a stay its nights (one by default),
 * anything else the offer's price; null without a price.
 */
export function bookingValue(
  offer: OfferItem | null,
  booking: { date: string; nights: number | null },
  businessCurrency: string,
): BookingValue | null {
  if (!offer) {
    return null;
  }
  const currency = offer.currency_code ?? businessCurrency;
  if (offer.kind === "room_type") {
    const minor = /^\d{4}-\d{2}-\d{2}$/.test(booking.date) ? stayValueMinor(offer, booking.date, booking.nights ?? 1) : null;
    return minor === null ? null : { minor, currency };
  }
  return offer.price_minor === null || offer.price_minor === undefined ? null : { minor: offer.price_minor, currency };
}

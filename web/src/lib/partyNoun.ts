/**
 * Who a booking is for, in the words of the niche: a table or a room seats
 * guests (a hotel counts guests and nights), a master, a bay or a car
 * serves clients, an arena or a class slot takes participants. So a salon
 * reads "1 client", never "1 guest".
 */

import type { ResourceKind } from "@/api/types";
import type { MessageKey, PluralKey } from "@/i18n/translate";

export type PartyNoun = "guests" | "clients" | "participants";

const NOUNS: Record<ResourceKind, PartyNoun> = {
  table: "guests",
  room: "guests",
  staff: "clients",
  bay: "clients",
  vehicle: "clients",
  arena: "participants",
  slot: "participants",
};

/** "3 guests", "1 client", "8 participants". */
export const PARTY_COUNT_KEYS: Record<PartyNoun, PluralKey> = {
  guests: "bookings.party.guests",
  clients: "bookings.party.clients",
  participants: "bookings.party.participants",
};

/** The party field's label: "Guests", "Clients", "Participants". */
export const PARTY_LABEL_KEYS: Record<PartyNoun, MessageKey> = {
  guests: "bookings.partyLabel.guests",
  clients: "bookings.partyLabel.clients",
  participants: "bookings.partyLabel.participants",
};

/**
 * The noun for a booking of a resource of `kind`, else of the niche's own
 * resource kind (a resource no longer listed), else "guests".
 */
export function partyNounFor(kind: ResourceKind | null | undefined, nicheKind?: ResourceKind | null): PartyNoun {
  const resolved = kind ?? nicheKind;
  return resolved ? NOUNS[resolved] : "guests";
}

/** The kind of the resource with `resourceId` among `resources`, if listed. */
export function resourceKindOf(
  resources: readonly { id: string; kind: ResourceKind }[],
  resourceId: string | null | undefined,
): ResourceKind | null {
  return resources.find((resource) => resource.id === resourceId)?.kind ?? null;
}

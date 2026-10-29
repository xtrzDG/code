"use client";

import { useNiche } from "@/api/catalog";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { ResourceKind } from "@/api/types";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { useI18n } from "@/i18n/client";
import { PARTY_COUNT_KEYS, PARTY_LABEL_KEYS, partyNounFor, resourceKindOf, type PartyNoun } from "@/lib/partyNoun";

export interface PartyWording {
  /** The noun for a booking of this resource (or of the niche's own kind). */
  noun: (resourceId?: string | null) => PartyNoun;
  /** "3 guests", "1 client". */
  count: (size: number, resourceId?: string | null) => string;
  /** The party field's label for a booking of this resource: "Guests", "Clients". */
  label: (resourceId?: string | null) => string;
}

/**
 * Who bookings are for, in the business's words: the booked resource's
 * kind decides (a table seats guests, a master serves clients), else the
 * niche's. The resources list is the one the bookings page reads (cached).
 */
export function usePartyWording(options: { kind?: ResourceKind | null } = {}): PartyWording {
  const { t, tp } = useI18n();
  const { business } = useBusiness();
  const niche = useNiche(business.niche_key);
  const resources = useQuery(queryKeys.resources.list(business.id), () =>
    api.GET("/v1/businesses/{business_id}/resources", { params: { path: { business_id: business.id } } }),
  );
  const nicheKind = niche.data?.niche.resource_kind ?? null;
  const noun = (resourceId?: string | null) =>
    partyNounFor(resourceKindOf(resources.data?.items ?? [], resourceId) ?? options.kind ?? null, nicheKind);
  return {
    noun,
    count: (size, resourceId) => tp(PARTY_COUNT_KEYS[noun(resourceId)], size),
    label: (resourceId) => t(PARTY_LABEL_KEYS[noun(resourceId)]),
  };
}

"use client";

/**
 * The palette's search of a business (GET /v1/businesses/{id}/search?q=):
 * customers, conversations and bookings, a few of each, as palette
 * entries. It asks once the text holds two characters and the typing has
 * paused; a found customer's phone is masked for staff the owner did not
 * allow to see phones (the API decides). Every search that finds someone
 * is written to the audit log by the API.
 */

import { useEffect, useState } from "react";

import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { queryKeys } from "@/api/queryKeys";
import type { Schema } from "@/api/types";
import { useQuery } from "@/api/useQuery";
import { CHANNEL_LABELS } from "@/components/insights/labels";
import { useI18n } from "@/i18n/client";
import { searchTextOf, type PaletteEntry, type PaletteGroup } from "@/lib/commandPalette";
import { formatDateTime } from "@/lib/format";
import { customerPath, conversationPath } from "@/lib/navigation";
import { formatPhone } from "@/lib/phone";

type SearchResults = Schema<"BusinessSearchResults">;

/** Where the palette searches: the business and its time zone (the dates of hits). */
export interface PaletteSearchScope {
  businessId: string;
  timeZone: string;
}

export interface PaletteSearch {
  groups: Partial<Record<PaletteGroup, PaletteEntry[]>>;
  /** The text searched (null: too short to search). */
  searched: string | null;
  isSearching: boolean;
  error: ApiError | null;
}

const TYPING_PAUSE_MS = 250;

function useSettledText(text: string): string | null {
  const [settled, setSettled] = useState<string | null>(null);
  useEffect(() => {
    const timer = window.setTimeout(() => setSettled(searchTextOf(text)), TYPING_PAUSE_MS);
    return () => window.clearTimeout(timer);
  }, [text]);
  return settled;
}

export function useCommandPaletteSearch(scope: PaletteSearchScope | null, text: string): PaletteSearch {
  const { t, tp, locale } = useI18n();
  const settled = useSettledText(text);
  const searched = scope ? settled : null;
  const businessId = scope?.businessId ?? "";
  const results = useQuery<SearchResults>(
    queryKeys.customers.search(businessId, searched ?? ""),
    () =>
      api.GET("/v1/businesses/{business_id}/search", {
        params: { path: { business_id: businessId }, query: { q: searched ?? "" } },
      }),
    { enabled: searched !== null, staleMs: 10_000 },
  );
  const data = searched !== null ? results.data : undefined;
  const when = (value: number) => formatDateTime(value, { locale, timeZone: scope?.timeZone ?? "UTC" });
  const unnamed = t("palette.unnamed");

  const customers: PaletteEntry[] = (data?.customers ?? []).map((customer) => {
    const phone = customer.phone_number ? formatPhone(customer.phone_number) : customer.masked_phone_number;
    return {
      id: `customer:${customer.id}`,
      group: "customers",
      label: customer.name ?? phone ?? unnamed,
      detail: customer.name ? (phone ?? undefined) : undefined,
      href: customerPath(businessId, customer.id),
    };
  });
  const conversations: PaletteEntry[] = (data?.conversations ?? []).map((hit) => ({
    id: `conversation:${hit.id}`,
    group: "conversations",
    label: hit.contact_name ?? unnamed,
    detail: t("palette.conversationDetail", { channel: t(CHANNEL_LABELS[hit.channel]), date: when(hit.last_message_at) }),
    href: conversationPath(businessId, hit.id),
  }));
  const bookings: PaletteEntry[] = (data?.bookings ?? []).map((hit) => ({
    id: `booking:${hit.id}`,
    group: "bookings",
    label: hit.contact_name ?? unnamed,
    detail: t("palette.bookingDetail", {
      date: when(hit.starts_at * 1_000_000),
      guests: tp("palette.partySize", hit.party_size),
    }),
    href: customerPath(businessId, hit.contact_id),
  }));

  return {
    groups: { customers, conversations, bookings },
    searched,
    isSearching: searched !== null && (results.isLoading || results.isFetching || settled !== searchTextOf(text)),
    error: searched !== null ? results.error : null,
  };
}

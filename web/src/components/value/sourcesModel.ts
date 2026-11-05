/**
 * Pure rules of "Where customers came from" (Reports) and the source chip
 * of the inbox: how a source tag reads to people, and the totals of the
 * table.
 */

import type { Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

export type CustomerSources = Schema<"CustomerSourcesView">;
export type CustomerSourceRow = Schema<"CustomerSourceRow">;

export const SOURCE_PERIODS = ["7d", "30d", "90d"] as const;
export type SourcePeriod = (typeof SOURCE_PERIODS)[number];
export const DEFAULT_SOURCE_PERIOD: SourcePeriod = "30d";

/** The share card's places (Channels → Share), read by their names. */
const SHARE_PLACES: Record<string, MessageKey> = {
  table: "share.sources.table",
  window: "share.sources.window",
  flyer: "share.sources.flyer",
  instagram: "share.sources.instagram",
  google: "share.sources.google",
  website: "share.sources.website",
  email: "share.sources.email",
};

const PHONE_TAG = /^tel-(\d{6,15})$/;
const AD_TAG = /^ad(?:-(.+))?$/;

/** How a source tag reads: a share card place, the line called, an ad, or the tag itself. */
export type SourceName =
  | { kind: "place"; key: MessageKey }
  | { kind: "phone"; number: string }
  | { kind: "ad"; id: string | null }
  | { kind: "tag"; tag: string };

export function sourceNameOf(tag: string): SourceName {
  const place = SHARE_PLACES[tag];
  if (place) {
    return { kind: "place", key: place };
  }
  const phone = PHONE_TAG.exec(tag);
  if (phone) {
    return { kind: "phone", number: `+${phone[1]}` };
  }
  const ad = AD_TAG.exec(tag);
  if (ad) {
    return { kind: "ad", id: ad[1] ?? null };
  }
  return { kind: "tag", tag };
}

export interface SourceTotals {
  conversations: number;
  bookings: number;
  requests: number;
  /** Null when no row has a value (nothing prices them). */
  valueMinor: number | null;
}

/** The sums of the table's rows. */
export function sourceTotals(rows: readonly CustomerSourceRow[]): SourceTotals {
  const valued = rows.filter((row) => row.estimated_value_minor !== null && row.estimated_value_minor !== undefined);
  return {
    conversations: rows.reduce((sum, row) => sum + row.conversation_count, 0),
    bookings: rows.reduce((sum, row) => sum + row.booking_count, 0),
    requests: rows.reduce((sum, row) => sum + row.request_count, 0),
    valueMinor: valued.length === 0 ? null : valued.reduce((sum, row) => sum + (row.estimated_value_minor ?? 0), 0),
  };
}

/** A row's share of the period's conversations, in whole percent (for its bar). */
export function conversationShare(row: CustomerSourceRow, totals: SourceTotals): number {
  return totals.conversations === 0 ? 0 : Math.round((row.conversation_count / totals.conversations) * 100);
}

/** Whether the table has anything tagged: without tags it only splits by channel. */
export function hasTaggedSources(rows: readonly CustomerSourceRow[]): boolean {
  return rows.some((row) => row.kind !== "untagged");
}

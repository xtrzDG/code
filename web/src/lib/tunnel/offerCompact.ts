/**
 * The offer of Assistant → Business profile on a phone, once it is long:
 * each saved line folds to one short row (name, price, minutes) that opens
 * for editing, lines of different kinds sit in folded groups with their
 * counts, and a search finds a line by its name.
 */

import type { KnowledgeItemKind } from "@/api/types";
import { kindHasDuration } from "@/lib/knowledge/kinds";
import type { OfferRow } from "@/lib/wizard/offers";

/** From this many lines a phone folds the offer; fewer stay the full table. */
export const COMPACT_OFFER_FROM = 6;

export interface OfferGroup<Row> {
  kind: KnowledgeItemKind;
  rows: Row[];
}

/** The lines by kind: the niche's kinds first in their order, then any other, each keeping the lines' order. */
export function groupByKind<Row extends Pick<OfferRow, "kind">>(rows: readonly Row[], order: readonly KnowledgeItemKind[]): OfferGroup<Row>[] {
  const groups = new Map<KnowledgeItemKind, Row[]>(order.map((kind) => [kind, []]));
  for (const row of rows) {
    groups.set(row.kind, [...(groups.get(row.kind) ?? []), row]);
  }
  return [...groups].filter(([, list]) => list.length > 0).map(([kind, list]) => ({ kind, rows: list }));
}

/** A text as search compares it: case and accents aside, so "cafe" finds "Café" and "ёлка" finds "Елка". */
function folded(text: string, locale: string): string {
  return text.normalize("NFD").replace(/\p{M}/gu, "").toLocaleLowerCase(locale);
}

/** Whether a line's name holds what was searched (an empty search holds every line). */
export function matchesQuery(title: string, query: string, locale: string): boolean {
  const needle = folded(query.trim(), locale);
  return needle === "" || folded(title, locale).includes(needle);
}

/** The minutes a folded row shows: only for a kind that lasts a while, and only when typed as a whole number. */
export function rowMinutes(row: Pick<OfferRow, "kind" | "duration">): number | null {
  const minutes = Number(row.duration.trim());
  return kindHasDuration(row.kind) && row.duration.trim() !== "" && Number.isInteger(minutes) && minutes > 0 ? minutes : null;
}

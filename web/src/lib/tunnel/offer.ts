/**
 * "What you offer" in the tunnel: a short table of names and prices that
 * saves itself. It starts from what the business already has (saved or
 * imported items) and the niche's examples ("Women's haircut", without a
 * price). An example is only a suggestion: it is saved once the owner
 * gives it a price or edits it, never as it came, so the assistant never
 * offers something the business does not sell.
 */

import type { KnowledgeItemDetails, KnowledgeItemKind, RequestBody, Schema } from "@/api/types";
import { majorToMinor, parseDecimalInput } from "@/lib/format";
import { isOfferRowChanged, newOfferRow, offerRowFromItem, validateOfferRow, type OfferRow } from "@/lib/wizard/offers";

/** Kinds that are not on the offer table (they have their own places). */
const NOT_OFFERS: ReadonlySet<KnowledgeItemKind> = new Set(["faq", "policy"]);

export interface TunnelOfferRow extends OfferRow {
  /** A niche example nobody touched yet: shown, not saved. */
  isSuggestion: boolean;
}

export function isOfferItem(item: Pick<KnowledgeItemDetails, "kind" | "is_active">): boolean {
  return !NOT_OFFERS.has(item.kind) && item.is_active;
}

/**
 * The table's first rows: the business's offer items, then the niche's
 * examples whose name is not there yet.
 */
export function initialOfferRows(
  items: readonly KnowledgeItemDetails[],
  examples: readonly Schema<"StarterOfferView">[],
  currency: string,
): TunnelOfferRow[] {
  const saved = items.filter(isOfferItem).map((item) => ({ ...offerRowFromItem(item, currency), isSuggestion: false }));
  const names = new Set(saved.map((row) => row.title.trim().toLocaleLowerCase()));
  const suggestions = examples
    .filter((example) => !names.has(example.title.trim().toLocaleLowerCase()))
    .map((example) => ({
      ...newOfferRow(example.kind, `starter-${example.key}`),
      title: example.title,
      duration: example.duration_minutes ? String(example.duration_minutes) : "",
      isSuggestion: true,
    }));
  return [...saved, ...suggestions];
}

export function blankOfferRow(kind: KnowledgeItemKind, key: string): TunnelOfferRow {
  return { ...newOfferRow(kind, key), isSuggestion: false };
}

/** A field typed into: a suggestion becomes the owner's row. */
export function editOfferRow(row: TunnelOfferRow, patch: Partial<Pick<OfferRow, "title" | "price" | "duration">>): TunnelOfferRow {
  return { ...row, ...patch, isSuggestion: false };
}

export type KnowledgeItemCreate = RequestBody<"/v1/businesses/{business_id}/knowledge", "post">;
export type KnowledgeItemChange = RequestBody<"/v1/businesses/{business_id}/knowledge/{item_id}", "patch">;

export type OfferSave =
  | { kind: "none" }
  | { kind: "invalid" }
  | { kind: "create"; body: KnowledgeItemCreate }
  | { kind: "update"; id: string; body: KnowledgeItemChange };

function priceMinor(row: OfferRow, currency: string): number | null {
  const price = parseDecimalInput(row.price, currency);
  return price === null ? null : majorToMinor(price, currency);
}

function durationMinutes(row: OfferRow): number | null {
  return row.duration.trim() ? Number(row.duration.trim()) : null;
}

/** What saving a row means now: nothing, not yet (invalid), a new item or a change. */
export function offerSave(row: TunnelOfferRow, currency: string): OfferSave {
  if (row.isSuggestion || row.title.trim() === "" || !isOfferRowChanged(row)) {
    return { kind: "none" };
  }
  if (Object.keys(validateOfferRow(row, currency)).length > 0) {
    return { kind: "invalid" };
  }
  const fields = {
    kind: row.kind,
    title: row.title.trim(),
    price_minor: priceMinor(row, currency),
    duration_minutes: durationMinutes(row),
  };
  return row.id ? { kind: "update", id: row.id, body: fields } : { kind: "create", body: { ...fields, is_active: true } };
}

/** The row after the API stored it: its id and a new baseline. */
export function savedOfferRow(row: TunnelOfferRow, item: KnowledgeItemDetails, currency: string): TunnelOfferRow {
  const stored = offerRowFromItem(item, currency);
  return { ...row, id: item.id, baseline: stored.baseline === null ? null : snapshotOf(row, stored) };
}

/**
 * The baseline of what the owner sees: the stored item's, unless they
 * typed on while the save was under way (then the row stays changed).
 */
function snapshotOf(row: TunnelOfferRow, stored: OfferRow): string | null {
  const typed = { ...stored, title: row.title, price: row.price, duration: row.duration };
  return isOfferRowChanged(typed) ? stored.baseline : typed.baseline;
}

/** Rows the owner gave a name and a price: the count shown and needed for "done". */
export function pricedCount(rows: readonly TunnelOfferRow[], currency: string): number {
  return rows.filter((row) => !row.isSuggestion && row.title.trim() !== "" && priceMinor(row, currency) !== null).length;
}

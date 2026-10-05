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
import { kindHasDuration } from "@/lib/knowledge/kinds";
import { isOfferRowChanged, newOfferRow, offerRowFromItem, validateOfferRow, type OfferRow } from "@/lib/wizard/offers";

import { exampleRowKey } from "./offerMemory";
import type { PastedOffer } from "./offerPaste";

/** Kinds that are not on the offer table (they have their own places). */
const NOT_OFFERS: ReadonlySet<KnowledgeItemKind> = new Set(["faq", "policy"]);

export interface TunnelOfferRow extends OfferRow {
  /** A niche example nobody touched yet: shown, not saved. */
  isSuggestion: boolean;
}

export function isOfferItem(item: Pick<KnowledgeItemDetails, "kind" | "is_active">): boolean {
  return !NOT_OFFERS.has(item.kind) && item.is_active;
}

/** Oldest first, as the owner typed them (the API lists the newest first). */
function inTypedOrder(left: KnowledgeItemDetails, right: KnowledgeItemDetails): number {
  return left.created_at - right.created_at || left.id.localeCompare(right.id);
}

export interface InitialOfferOptions {
  /** Examples the owner replaced or removed (offerMemory), by example key. */
  done?: ReadonlySet<string>;
  /** The offer step was finished or skipped before: the owner has dealt with the examples. */
  isStepCompleted?: boolean;
}

/**
 * The table's first rows: the business's offer items in the order they
 * were added. The niche's examples are offered only to an empty table on
 * a step never finished: once anything is saved (in whatever language the
 * owner typed it: "Бизнес-ланч" is the example "Business lunch" as much as
 * "Business lunch" is) or the step was completed, a revisit shows exactly
 * what the business sells. Examples the owner dealt with are matched by
 * their key, never by a title, which changes with the language.
 */
export function initialOfferRows(
  items: readonly KnowledgeItemDetails[],
  examples: readonly Schema<"StarterOfferView">[],
  currency: string,
  { done = new Set(), isStepCompleted = false }: InitialOfferOptions = {},
): TunnelOfferRow[] {
  const saved = items
    .filter(isOfferItem)
    .sort(inTypedOrder)
    .map((item) => ({ ...offerRowFromItem(item, currency), isSuggestion: false }));
  if (saved.length > 0 || isStepCompleted) {
    return saved;
  }
  return examples
    .filter((example) => !done.has(example.key))
    .map((example) => ({
      ...newOfferRow(example.kind, exampleRowKey(example.key)),
      title: example.title,
      duration: example.duration_minutes ? String(example.duration_minutes) : "",
      isSuggestion: true,
    }));
}

export function blankOfferRow(kind: KnowledgeItemKind, key: string): TunnelOfferRow {
  return { ...newOfferRow(kind, key), isSuggestion: false };
}

/**
 * A field typed into: a suggestion becomes the owner's row. A kind that
 * lasts no time (a dish, a product) drops the duration.
 */
export function editOfferRow(row: TunnelOfferRow, patch: Partial<Pick<OfferRow, "title" | "price" | "duration" | "kind">>): TunnelOfferRow {
  const edited = { ...row, ...patch, isSuggestion: false };
  return kindHasDuration(edited.kind) ? edited : { ...edited, duration: "" };
}

/** Lines pasted from a spreadsheet as new rows of one kind (`keys` names them). */
export function pastedOfferRows(pasted: readonly PastedOffer[], kind: KnowledgeItemKind, keys: (index: number) => string): TunnelOfferRow[] {
  return pasted.map((offer, index) => editOfferRow(blankOfferRow(kind, keys(index)), { title: offer.title, price: offer.price, duration: offer.duration }));
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

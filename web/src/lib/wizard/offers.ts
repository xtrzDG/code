/**
 * Pure helpers of the profile wizard's offer step: offer rows of the form,
 * their validation and the knowledge items sent to the API.
 */

import type { KnowledgeItemDetails, KnowledgeItemKind } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

import {
  MONEY_INPUT_MESSAGES,
  currencyFractionDigits,
  decimalInputValue,
  majorToMinor,
  minorToMajor,
  moneyInputProblem,
  parseDecimalInput,
} from "../format";

/** Kinds of things a business sells (FAQ and rules have their own step). */
export function offerKinds(knowledgeKinds: readonly KnowledgeItemKind[]): KnowledgeItemKind[] {
  const kinds = knowledgeKinds.filter((kind) => kind !== "faq" && kind !== "policy");
  return kinds.length > 0 ? kinds : ["service"];
}

/** One offer row of the form; prices and durations are kept as typed text. */
export interface OfferRow {
  key: string;
  id: string | null;
  kind: KnowledgeItemKind;
  title: string;
  body: string;
  price: string;
  duration: string;
  /** Fields of the item the API does not show in this step, kept on save. */
  kept: Pick<KnowledgeItemDetails, "tags" | "attributes" | "languages" | "is_active">;
  /** Snapshot of the last saved values; a row differs from it when edited. */
  baseline: string | null;
}

function offerSnapshot(row: Pick<OfferRow, "kind" | "title" | "body" | "price" | "duration">): string {
  return JSON.stringify([row.kind, row.title.trim(), row.body.trim(), row.price.trim(), row.duration.trim()]);
}

export function offerRowFromItem(item: KnowledgeItemDetails, currency: string): OfferRow {
  const row: OfferRow = {
    key: item.id,
    id: item.id,
    kind: item.kind,
    title: item.title,
    body: item.body ?? "",
    price:
      item.price_minor === null || item.price_minor === undefined
        ? ""
        : decimalInputValue(minorToMajor(item.price_minor, currency), currencyFractionDigits(currency)),
    duration: item.duration_minutes ? String(item.duration_minutes) : "",
    kept: {
      tags: item.tags ?? [],
      attributes: item.attributes ?? [],
      languages: item.languages ?? [],
      is_active: item.is_active,
    },
    baseline: null,
  };
  row.baseline = offerSnapshot(row);
  return row;
}

export function newOfferRow(kind: KnowledgeItemKind, key: string): OfferRow {
  return {
    key,
    id: null,
    kind,
    title: "",
    body: "",
    price: "",
    duration: "",
    kept: { tags: [], attributes: [], languages: [], is_active: true },
    baseline: null,
  };
}

export function isOfferRowChanged(row: OfferRow): boolean {
  return row.baseline !== offerSnapshot(row);
}

export interface OfferRowErrors {
  title?: MessageKey;
  price?: MessageKey;
  duration?: MessageKey;
}

export function validateOfferRow(row: OfferRow, currency: string): OfferRowErrors {
  const errors: OfferRowErrors = {};
  const isBlank = row.title.trim() === "" && row.body.trim() === "" && row.price.trim() === "" && row.duration.trim() === "";
  if (isBlank) {
    return errors;
  }
  if (row.title.trim() === "") {
    errors.title = "validation.required";
  }
  const priceProblem = row.price.trim() === "" ? null : moneyInputProblem(row.price, currency);
  if (priceProblem) {
    errors.price = MONEY_INPUT_MESSAGES[priceProblem];
  }
  if (row.duration.trim() !== "" && !/^\d+$/.test(row.duration.trim())) {
    errors.duration = "validation.wholeNumber";
  } else if (row.duration.trim() !== "" && Number(row.duration) <= 0) {
    errors.duration = "validation.positive";
  }
  return errors;
}

export interface KnowledgeItemUpsert {
  id?: string | null;
  kind: KnowledgeItemKind;
  title: string;
  body?: string | null;
  price_minor?: number | null;
  duration_minutes?: number | null;
  tags?: string[];
  attributes?: { key: string; value: string }[];
  languages?: string[];
  is_active?: boolean;
}

/** Rows to send: new or edited ones with a title. */
export function offerItemsPayload(rows: readonly OfferRow[], currency: string): KnowledgeItemUpsert[] {
  return rows
    .filter((row) => row.title.trim() !== "" && isOfferRowChanged(row))
    .map((row) => {
      const price = parseDecimalInput(row.price, currency);
      return {
        ...(row.id ? { id: row.id } : {}),
        kind: row.kind,
        title: row.title.trim(),
        body: row.body.trim() || null,
        price_minor: price === null ? null : majorToMinor(price, currency),
        duration_minutes: row.duration.trim() ? Number(row.duration.trim()) : null,
        tags: row.kept.tags,
        attributes: row.kept.attributes,
        languages: row.kept.languages,
        is_active: row.kept.is_active,
      };
    });
}

/**
 * After a save: rows the API stored get their id and become the new
 * baseline (matched by id, else by kind and title).
 */
export function markOfferRowsSaved(rows: readonly OfferRow[], saved: readonly KnowledgeItemDetails[]): OfferRow[] {
  return rows.map((row) => {
    if (row.title.trim() === "" || !isOfferRowChanged(row)) {
      return row;
    }
    const match = saved.find(
      (item) =>
        (row.id !== null && item.id === row.id) ||
        (item.kind === row.kind && item.title.trim().toLocaleLowerCase() === row.title.trim().toLocaleLowerCase()),
    );
    return match ? { ...row, id: match.id, baseline: offerSnapshot(row) } : row;
  });
}

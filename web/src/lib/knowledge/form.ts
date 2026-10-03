/**
 * The Knowledge section's item form: its values, validation and the API
 * bodies to create or change an item.
 *
 * Prices are typed in major units ("18,50") and sent in minor units of the
 * business currency (1850).
 */

import type { KnowledgeItemDetails, KnowledgeItemKind, RequestBody } from "@/api/types";
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
import { kindHasPrice } from "./kinds";

export type KnowledgeItemCreateBody = RequestBody<"/v1/businesses/{business_id}/knowledge", "post">;
export type KnowledgeItemPatchBody = RequestBody<"/v1/businesses/{business_id}/knowledge/{item_id}", "patch">;

export const MAX_TITLE_LENGTH = 300;
export const MAX_BODY_LENGTH = 8000;
export const MAX_DURATION_MINUTES = 43_200;

/** The editor's values; price and duration are kept as typed. */
export interface KnowledgeForm {
  kind: KnowledgeItemKind;
  title: string;
  body: string;
  price: string;
  duration: string;
  languages: string[];
  isActive: boolean;
}

export type KnowledgeFormErrors = Partial<Record<"title" | "body" | "price" | "duration", MessageKey>>;

export function emptyKnowledgeForm(kind: KnowledgeItemKind): KnowledgeForm {
  return { kind, title: "", body: "", price: "", duration: "", languages: [], isActive: true };
}

type FormSource = Pick<KnowledgeItemDetails, "kind" | "title" | "body" | "price_minor" | "duration_minutes"> &
  Partial<Pick<KnowledgeItemDetails, "languages" | "is_active">>;

export function knowledgeFormFromItem(item: FormSource, currency: string): KnowledgeForm {
  return {
    kind: item.kind,
    title: item.title,
    body: item.body ?? "",
    price:
      item.price_minor === null || item.price_minor === undefined
        ? ""
        : decimalInputValue(minorToMajor(item.price_minor, currency), currencyFractionDigits(currency)),
    duration: item.duration_minutes ? String(item.duration_minutes) : "",
    languages: [...(item.languages ?? [])],
    isActive: item.is_active ?? true,
  };
}

export function validateKnowledgeForm(form: KnowledgeForm, currency: string): KnowledgeFormErrors {
  const errors: KnowledgeFormErrors = {};
  const title = form.title.trim();
  const body = form.body.trim();
  if (title === "") {
    errors.title = "validation.required";
  } else if (title.length > MAX_TITLE_LENGTH) {
    errors.title = "validation.tooLong";
  }
  if (form.kind === "faq" && body === "") {
    errors.body = "validation.required";
  } else if (body.length > MAX_BODY_LENGTH) {
    errors.body = "validation.tooLong";
  }
  if (kindHasPrice(form.kind) && form.price.trim() !== "") {
    const problem = moneyInputProblem(form.price, currency);
    if (problem) {
      errors.price = MONEY_INPUT_MESSAGES[problem];
    }
  }
  const duration = form.duration.trim();
  if (duration !== "") {
    if (!/^\d+$/.test(duration)) {
      errors.duration = "validation.wholeNumber";
    } else if (Number(duration) < 1 || Number(duration) > MAX_DURATION_MINUTES) {
      errors.duration = "validation.positive";
    }
  }
  return errors;
}

function priceMinor(form: KnowledgeForm, currency: string): number | null {
  if (!kindHasPrice(form.kind)) {
    return null;
  }
  const price = parseDecimalInput(form.price, currency);
  return price === null ? null : majorToMinor(price, currency);
}

function durationMinutes(form: KnowledgeForm): number | null {
  const duration = form.duration.trim();
  return duration === "" ? null : Number(duration);
}

/** Body of POST …/knowledge for a validated form. */
export function knowledgeCreateBody(form: KnowledgeForm, currency: string): KnowledgeItemCreateBody {
  return {
    kind: form.kind,
    title: form.title.trim(),
    body: form.body.trim() || null,
    price_minor: priceMinor(form, currency),
    duration_minutes: durationMinutes(form),
    languages: form.languages,
    is_active: form.isActive,
  };
}

function sameLanguages(left: readonly string[], right: readonly string[]): boolean {
  return left.length === right.length && [...left].sort().join(",") === [...right].sort().join(",");
}

/**
 * Body of PATCH …/knowledge/{id}: only what changed against `initial`
 * (an explicit null clears body, price or duration). Empty when nothing changed.
 */
export function knowledgePatchBody(form: KnowledgeForm, initial: KnowledgeForm, currency: string): KnowledgeItemPatchBody {
  const patch: KnowledgeItemPatchBody = {};
  if (form.kind !== initial.kind) {
    patch.kind = form.kind;
  }
  if (form.title.trim() !== initial.title.trim()) {
    patch.title = form.title.trim();
  }
  if (form.body.trim() !== initial.body.trim()) {
    patch.body = form.body.trim() || null;
  }
  const price = priceMinor(form, currency);
  if (price !== priceMinor(initial, currency)) {
    patch.price_minor = price;
  }
  const duration = durationMinutes(form);
  if (duration !== durationMinutes(initial)) {
    patch.duration_minutes = duration;
  }
  if (!sameLanguages(form.languages, initial.languages)) {
    patch.languages = form.languages;
  }
  if (form.isActive !== initial.isActive) {
    patch.is_active = form.isActive;
  }
  return patch;
}

export function isEmptyPatch(patch: KnowledgeItemPatchBody): boolean {
  return Object.keys(patch).length === 0;
}

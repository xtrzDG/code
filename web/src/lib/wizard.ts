/**
 * Pure helpers of the profile wizard (app/b/[businessId]/onboarding):
 * niche answers, offer and FAQ rows, and their API bodies.
 */

import type { KnowledgeItemDetails, KnowledgeItemKind, WizardQuestionView } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

import {
  MONEY_INPUT_MESSAGES,
  currencyFractionDigits,
  decimalInputValue,
  majorToMinor,
  minorToMajor,
  moneyInputProblem,
  parseDecimalInput,
} from "./format";

// --- Niche answers ------------------------------------------------------------

/** One answer as the form holds it: text, or choice keys for choice questions. */
export interface AnswerValue {
  text: string;
  choices: string[];
}

export type AnswerValues = Record<string, AnswerValue>;

export interface ProfileAnswerInput {
  question_key: string;
  answer?: string | null;
  choice_keys?: string[];
}

const CHOICE_TYPES = new Set(["single_choice", "multiple_choice"]);

export function isChoiceQuestion(question: WizardQuestionView): boolean {
  return CHOICE_TYPES.has(question.question.answer_type);
}

/** Form values from the wizard's current answers. */
export function initialAnswers(questions: readonly WizardQuestionView[]): AnswerValues {
  const values: AnswerValues = {};
  for (const item of questions) {
    const selected = item.selected_choice_keys ?? [];
    if (isChoiceQuestion(item)) {
      const choices = selected.length > 0 ? selected : (item.answer ?? "").split(",").filter(Boolean);
      values[item.question.key] = { text: "", choices };
    } else {
      values[item.question.key] = { text: item.answer ?? selected[0] ?? "", choices: [] };
    }
  }
  return values;
}

/**
 * The `answers` of a step body. A step save replaces all answers of that
 * step, so every answered question is sent and empty ones are left out
 * (which clears them).
 */
export function answersPayload(
  questions: readonly WizardQuestionView[],
  values: AnswerValues,
): ProfileAnswerInput[] {
  const answers: ProfileAnswerInput[] = [];
  for (const item of questions) {
    const value = values[item.question.key];
    if (!value) {
      continue;
    }
    if (isChoiceQuestion(item)) {
      if (value.choices.length > 0) {
        answers.push({ question_key: item.question.key, choice_keys: value.choices });
      }
    } else if (value.text.trim() !== "") {
      answers.push({ question_key: item.question.key, answer: value.text.trim() });
    }
  }
  return answers;
}

const MAX_SHORT_TEXT = 300;
const MAX_LONG_TEXT = 4000;
const WEB_LINK = /^https?:\/\/[^\s/]+(\/\S*)?$/;

/** Problems the API would refuse, per question key. */
export function validateAnswers(
  questions: readonly WizardQuestionView[],
  values: AnswerValues,
): Record<string, MessageKey> {
  const errors: Record<string, MessageKey> = {};
  for (const item of questions) {
    const text = values[item.question.key]?.text.trim() ?? "";
    if (text === "") {
      continue;
    }
    switch (item.question.answer_type) {
      case "number":
        if (!/^\d+$/.test(text)) {
          errors[item.question.key] = "validation.wholeNumber";
        }
        break;
      case "url":
        if (!WEB_LINK.test(text) || text.length < 10) {
          errors[item.question.key] = "validation.url";
        }
        break;
      case "short_text":
        if (text.length > MAX_SHORT_TEXT) {
          errors[item.question.key] = "validation.tooLong";
        }
        break;
      case "long_text":
        if (text.length > MAX_LONG_TEXT) {
          errors[item.question.key] = "validation.tooLong";
        }
        break;
      default:
        break;
    }
  }
  return errors;
}

// --- Offer items ----------------------------------------------------------------

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

// --- FAQ ------------------------------------------------------------------------

export interface FaqRow {
  key: string;
  id: string | null;
  question: string;
  answer: string;
  languages: string[];
  baseline: string | null;
}

function faqSnapshot(row: Pick<FaqRow, "question" | "answer">): string {
  return JSON.stringify([row.question.trim(), row.answer.trim()]);
}

export function faqRowFromItem(item: KnowledgeItemDetails): FaqRow {
  const row: FaqRow = {
    key: item.id,
    id: item.id,
    question: item.title,
    answer: item.body ?? "",
    languages: item.languages ?? [],
    baseline: null,
  };
  row.baseline = faqSnapshot(row);
  return row;
}

export function newFaqRow(key: string): FaqRow {
  return { key, id: null, question: "", answer: "", languages: [], baseline: null };
}

export function isFaqRowChanged(row: FaqRow): boolean {
  return row.baseline !== faqSnapshot(row);
}

export function validateFaqRow(row: FaqRow): { question?: MessageKey; answer?: MessageKey } {
  if (row.question.trim() === "" && row.answer.trim() === "") {
    return {};
  }
  return {
    ...(row.question.trim() === "" ? { question: "validation.required" as const } : {}),
    ...(row.answer.trim() === "" ? { answer: "validation.required" as const } : {}),
  };
}

export interface FaqEntryInput {
  id?: string | null;
  question: string;
  answer: string;
  languages?: string[];
}

export function faqPayload(rows: readonly FaqRow[]): FaqEntryInput[] {
  return rows
    .filter((row) => row.question.trim() !== "" && row.answer.trim() !== "" && isFaqRowChanged(row))
    .map((row) => ({
      ...(row.id ? { id: row.id } : {}),
      question: row.question.trim(),
      answer: row.answer.trim(),
      languages: row.languages,
    }));
}

export function markFaqRowsSaved(rows: readonly FaqRow[], saved: readonly KnowledgeItemDetails[]): FaqRow[] {
  return rows.map((row) => {
    if (row.question.trim() === "" || !isFaqRowChanged(row)) {
      return row;
    }
    const match = saved.find(
      (item) =>
        item.kind === "faq" &&
        ((row.id !== null && item.id === row.id) ||
          item.title.trim().toLocaleLowerCase() === row.question.trim().toLocaleLowerCase()),
    );
    return match ? { ...row, id: match.id, baseline: faqSnapshot(row) } : row;
  });
}

/** Rule lists without blanks and repeats. */
export function cleanRules(rules: readonly string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const rule of rules) {
    const trimmed = rule.trim();
    const key = trimmed.toLocaleLowerCase();
    if (trimmed !== "" && !seen.has(key)) {
      seen.add(key);
      result.push(trimmed);
    }
  }
  return result;
}

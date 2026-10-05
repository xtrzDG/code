/**
 * Teaching the assistant from real conversations: "Fix this answer", the
 * reasons of a bad rating and the reply guard's verdict on an answer (the
 * owner's checks are in teachingChecks.ts). The pure rules the dialogs, the
 * conversation and the Overview share: which choices exist and what a form
 * needs before it is sent.
 */

import type { RequestBody, Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

import { majorToMinor, moneyInputProblem, parseDecimalInput, type MoneyInputProblem } from "./format";

export type CorrectionScope = Schema<"AnswerCorrectionScope">;
export type CorrectionDraft = Schema<"AnswerCorrectionDraft">;
export type CorrectionResult = Schema<"AnswerCorrectionResult">;
export type CorrectionBody = RequestBody<
  "/v1/businesses/{business_id}/conversations/{conversation_id}/messages/{message_id}/correction",
  "post"
>;
export type RatingReason = Schema<"ConversationRatingReason">;
export type Expectation = Schema<"AutotestExpectation">;
export type CheckSource = Schema<"AutotestCaseSource">;
export type CheckView = Schema<"AutotestCaseView">;
export type CheckBody = RequestBody<"/v1/businesses/{business_id}/autotest-cases", "post">;
export type CheckChanges = RequestBody<"/v1/businesses/{business_id}/autotest-cases/{case_id}", "patch">;
export type AnswerToImprove = Schema<"AnswerToImproveView">;
export type GuardView = Schema<"MessageGuardView">;
type GuardReason = Schema<"ReplyGuardReason">;

export const CORRECTION_SCOPES = ["faq", "price", "hours", "rule"] as const satisfies readonly CorrectionScope[];
export const RATING_REASONS = ["wrong_info", "should_hand_off", "tone", "too_long"] as const satisfies readonly RatingReason[];

export const SCOPE_LABELS: Record<CorrectionScope, MessageKey> = {
  faq: "teaching.fix.scopes.faq",
  price: "teaching.fix.scopes.price",
  hours: "teaching.fix.scopes.hours",
  rule: "teaching.fix.scopes.rule",
};

export const REASON_LABELS: Record<RatingReason, MessageKey> = {
  wrong_info: "teaching.rating.reasons.wrong_info",
  should_hand_off: "teaching.rating.reasons.should_hand_off",
  tone: "teaching.rating.reasons.tone",
  too_long: "teaching.rating.reasons.too_long",
};

const GUARD_REASON_LABELS: Record<GuardReason, MessageKey> = {
  unverified_values: "teaching.guard.reasons.unverified_values",
  unsupported_claims: "teaching.guard.reasons.unsupported_claims",
  personal_data: "teaching.guard.reasons.personal_data",
};

/** The words of the reply guard's reasons ("figures not in your details"). */
export function guardReasonKeys(reasons: readonly GuardReason[] | null | undefined): MessageKey[] {
  return (reasons ?? []).map((reason) => GUARD_REASON_LABELS[reason]);
}

/** Whether a scope asks for a price instead of a written answer. */
export function isPriceScope(scope: CorrectionScope): boolean {
  return scope === "price";
}

/**
 * The reply guard's chip on an assistant answer: rewritten once (warning)
 * or held back and passed to a person (danger), with why; nothing for a
 * clean answer or one stored before the guard kept verdicts.
 */
export function guardChip(
  guard: GuardView | null | undefined,
): { tone: "warning" | "danger"; label: MessageKey; reasons: MessageKey[] } | null {
  if (!guard || !guard.verdict || guard.verdict === "clean") {
    return null;
  }
  return {
    tone: guard.verdict === "handed_off" ? "danger" : "warning",
    label: guard.verdict === "handed_off" ? "teaching.guard.handed_off" : "teaching.guard.rewritten",
    reasons: guardReasonKeys(guard.reasons),
  };
}

/** The newest answer of the assistant among the messages (what a bad rating is about), or null. */
export function latestAnswerId(messages: readonly { id: string; author: string }[]): string | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message && message.author === "assistant") {
      return message.id;
    }
  }
  return null;
}

/** What the "Fix this answer" form holds while the owner writes. */
export interface CorrectionForm {
  scope: CorrectionScope;
  question: string;
  answer: string;
  /** A price list item to reprice (price only), or null for a new item named `question`. */
  itemId: string | null;
  price: string;
}

export type CorrectionProblem = "question" | "answer" | "price" | MoneyInputProblem;

/** The form the dialog opens with: the customer's question, and the price of the current fact. */
export function correctionFormOf(draft: CorrectionDraft): CorrectionForm {
  const fact = draft.current_fact ?? null;
  const isPriced = fact !== null && fact.price_minor !== null && fact.price_minor !== undefined;
  return {
    scope: draft.suggested_scope,
    question: draft.question ?? "",
    answer: draft.is_corrected && fact?.body ? fact.body : "",
    itemId: draft.suggested_scope === "price" && isPriced ? fact.knowledge_item_id : null,
    price: "",
  };
}

/** Why the form cannot be sent yet (empty: it can). */
export function correctionProblems(form: CorrectionForm, currency: string): CorrectionProblem[] {
  if (isPriceScope(form.scope)) {
    const problems: CorrectionProblem[] = [];
    if (form.itemId === null && form.question.trim() === "") {
      problems.push("question");
    }
    const priceProblem = form.price.trim() === "" ? "price" : moneyInputProblem(form.price, currency);
    if (priceProblem !== null) {
      problems.push(priceProblem);
    }
    return problems;
  }
  return [
    ...(form.question.trim() === "" ? (["question"] as const) : []),
    ...(form.answer.trim() === "" ? (["answer"] as const) : []),
  ];
}

/** The API body of a checked form (call `correctionProblems` first). */
export function correctionBody(form: CorrectionForm, currency: string): CorrectionBody {
  if (isPriceScope(form.scope)) {
    const price = parseDecimalInput(form.price, currency) ?? 0;
    return {
      scope: form.scope,
      knowledge_item_id: form.itemId,
      question: form.itemId === null ? form.question.trim() : null,
      correct_answer: form.answer.trim() || null,
      price_minor: majorToMinor(price, currency),
    };
  }
  return { scope: form.scope, question: form.question.trim(), correct_answer: form.answer.trim() };
}

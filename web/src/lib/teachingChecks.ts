/**
 * The owner's own checks ("My checks"): the choices a check has, what its
 * form needs before it is sent, the forms saved from a fixed answer, a bad
 * rating or a question without an answer, and how its latest result reads.
 */

import type { Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

import { minorToMajor } from "./format";
import type {
  AnswerToImprove,
  CheckBody,
  CheckChanges,
  CheckSource,
  CheckView,
  CorrectionResult,
  Expectation,
  RatingReason,
} from "./teaching";

type CheckCode = Schema<"AutotestCheckCode">;

export const EXPECTATIONS = [
  "must_mention",
  "must_not_mention",
  "must_hand_off",
  "must_create_lead",
] as const satisfies readonly Expectation[];

/** The longest question and expected text the API keeps. */
export const CHECK_QUESTION_MAX_LENGTH = 500;
export const EXPECTED_TEXT_MAX_LENGTH = 200;

export const EXPECTATION_LABELS: Record<Expectation, MessageKey> = {
  must_mention: "teaching.checks.expectations.must_mention",
  must_not_mention: "teaching.checks.expectations.must_not_mention",
  must_hand_off: "teaching.checks.expectations.must_hand_off",
  must_create_lead: "teaching.checks.expectations.must_create_lead",
};

export const SOURCE_LABELS: Record<CheckSource, MessageKey> = {
  owner: "teaching.checks.sources.owner",
  correction: "teaching.checks.sources.correction",
  unanswered_question: "teaching.checks.sources.unanswered_question",
  bad_rating: "teaching.checks.sources.bad_rating",
};

/** Why a check failed, in the owner's words (other codes: the outcome says it all). */
const CODE_LABELS: Partial<Record<CheckCode, MessageKey>> = {
  expected_text_missing: "teaching.checks.codes.expected_text_missing",
  forbidden_text_mentioned: "teaching.checks.codes.forbidden_text_mentioned",
  not_handed_off: "teaching.checks.codes.not_handed_off",
  no_lead_created: "teaching.checks.codes.no_lead_created",
};

/** Whether the answer must (not) name a text the check keeps. */
export function needsExpectedText(expectation: Expectation): boolean {
  return expectation === "must_mention" || expectation === "must_not_mention";
}


/** What a check form holds: new, edited, or saved from a conversation or a question. */
export interface CheckForm {
  question: string;
  expectation: Expectation;
  expectedText: string;
  language: string;
  source: CheckSource;
  sourceConversationId: string | null;
  sourceMessageId: string | null;
  sourceQuestionId: string | null;
}

export type CheckProblem = "question" | "expectedText";

/** An empty check in the business's default language. */
export function newCheckForm(language: string): CheckForm {
  return {
    question: "",
    expectation: "must_mention",
    expectedText: "",
    language,
    source: "owner",
    sourceConversationId: null,
    sourceMessageId: null,
    sourceQuestionId: null,
  };
}

/** A stored check, to change it. */
export function checkFormOf(check: CheckView): CheckForm {
  return {
    question: check.question,
    expectation: check.expectation,
    expectedText: check.expected_text ?? "",
    language: check.language,
    source: check.source,
    sourceConversationId: check.source_conversation_id ?? null,
    sourceMessageId: null,
    sourceQuestionId: null,
  };
}

/** A check saved from a correction: the same question must now get the corrected fact. */
export function checkFormFromCorrection(result: CorrectionResult, currency: string): CheckForm {
  const price = result.item.price_minor;
  return {
    ...newCheckForm(result.language),
    question: result.question,
    expectedText: price !== null && price !== undefined ? priceWords(price, currency) : "",
    source: "correction",
    sourceConversationId: result.conversation_id,
    sourceMessageId: result.message_id,
  };
}

/** A check saved from an answer worth improving (a bad rating or a question without an answer). */
export function checkFormFromItem(item: AnswerToImprove, language: string): CheckForm {
  const isQuestion = item.kind === "unanswered_question";
  return {
    ...newCheckForm(item.language ?? language),
    question: (isQuestion ? item.question : item.customer_message) ?? "",
    expectation: item.rating_reason === "should_hand_off" ? "must_hand_off" : "must_mention",
    source: isQuestion ? "unanswered_question" : "bad_rating",
    sourceConversationId: item.conversation_id ?? null,
    sourceMessageId: item.message_id ?? null,
    sourceQuestionId: item.question_id ?? null,
  };
}

/**
 * A check saved from a conversation rated bad: the customer's words before
 * the rated answer (the last ones when no answer is named), and a handoff
 * when the answer should have passed it to a person.
 */
export function checkFormFromRating(
  messages: readonly { id: string; author: string; text: string }[],
  conversation: { id: string; language?: string | null; rating_reason?: RatingReason | null },
  answerId: string | null,
  language: string,
): CheckForm {
  const end = answerId === null ? messages.length : messages.findIndex((message) => message.id === answerId);
  const before = messages.slice(0, end < 0 ? messages.length : end);
  const asked = [...before].reverse().find((message) => message.author === "customer" && message.text.trim() !== "");
  return {
    ...newCheckForm(conversation.language ?? language),
    question: asked?.text.trim() ?? "",
    expectation: conversation.rating_reason === "should_hand_off" ? "must_hand_off" : "must_mention",
    source: "bad_rating",
    sourceConversationId: conversation.id,
    sourceMessageId: answerId,
  };
}

/** "15" for 1500 tetri, "18.5" for 1850: the number an answer with the price contains. */
function priceWords(minor: number, currency: string): string {
  return String(minorToMajor(minor, currency));
}

export function checkProblems(form: CheckForm): CheckProblem[] {
  return [
    ...(form.question.trim() === "" ? (["question"] as const) : []),
    ...(needsExpectedText(form.expectation) && !/[\p{L}\p{N}]/u.test(form.expectedText)
      ? (["expectedText"] as const)
      : []),
  ];
}

/** The API body of a new check (call `checkProblems` first). */
export function checkBody(form: CheckForm): CheckBody {
  return {
    question: form.question.trim(),
    expectation: form.expectation,
    expected_text: needsExpectedText(form.expectation) ? form.expectedText.trim() : null,
    language: form.language,
    source: form.source,
    source_conversation_id: form.sourceConversationId,
    source_message_id: form.sourceMessageId,
    source_question_id: form.sourceQuestionId,
  };
}

/** The changes of an edited check. */
export function checkChanges(form: CheckForm): CheckChanges {
  return {
    question: form.question.trim(),
    expectation: form.expectation,
    expected_text: needsExpectedText(form.expectation) ? form.expectedText.trim() : null,
    language: form.language,
  };
}

/** How the latest run of a check reads: not run yet, passed or failed (with the version). */
export function checkResultTone(check: CheckView): "neutral" | "success" | "danger" | "warning" {
  const outcome = check.last_result?.outcome;
  if (!outcome) {
    return "neutral";
  }
  return outcome === "passed" ? "success" : outcome === "failed" ? "danger" : "warning";
}

/** The reasons of the latest failure the owner can act on, as texts. */
export function checkResultReasons(check: CheckView): MessageKey[] {
  return (check.last_result?.check_codes ?? []).flatMap((code) => {
    const label = CODE_LABELS[code];
    return label ? [label] : [];
  });
}

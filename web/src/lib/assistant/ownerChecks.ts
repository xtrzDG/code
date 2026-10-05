/**
 * The owner's own checks in the story of an update: which of them are
 * still pending, which failed in a run (named by their question, never as
 * "Your check"), the sentence that names a failure ("Your check did not
 * pass: “Can I come with my dog?” — the answer must pass the customer to a
 * person"), and whether anything is still not with customers.
 */

import type { Schema } from "@/api/types";
import type { Translator } from "@/i18n/translate";
import type { SentenceWithUserValues } from "@/i18n/userValues";
import { businessPath } from "@/lib/navigation";

import type { AutotestScenarioResult } from "./autotests";
import type { PendingChangesView } from "./pendingChanges";

export type Expectation = Schema<"AutotestExpectation">;
export type PendingOwnerCheck = Schema<"PendingOwnerCheckView">;
export type PendingDraft = Schema<"PendingDraftView">;
export type OwnerCheckOutcome = Schema<"OwnerCheckOutcomeView">;

type Words = Pick<Translator, "t">;

/** What a check asks, wherever it comes from (a check, a pending entry, a run's result, an outcome). */
export interface AskedCheck {
  question: string;
  expectation: Expectation;
  expected_text?: string | null;
}

/** A failed check with what fixes it: the check to open and the test answer to fix. */
export interface NamedFailure extends AskedCheck {
  checkId: string | null;
  conversationId: string | null;
  answerMessageId: string | null;
  answer: string | null;
  reason: string | null;
}

/*
 * The sentences below name the owner's own words (the question, the words
 * the answer must mention): each comes as its translation with those
 * placeholders left in and the words apart (`UserSentence` shows them as
 * user content).
 */

/** "the answer must mention “20 GEL”" in the owner's language. */
export function expectationSentence(check: Pick<AskedCheck, "expectation" | "expected_text">, words: Words): SentenceWithUserValues {
  return { text: words.t(`updates.expectation.${check.expectation}`), values: { text: check.expected_text?.trim() ?? "" } };
}

/** "Your check did not pass: “…” — the answer must pass the customer to a person". */
export function failureSentence(check: AskedCheck, words: Words): SentenceWithUserValues {
  const expectation = expectationSentence(check, words);
  return {
    text: words.t("updates.failed.one", { expectation: expectation.text }),
    values: { ...expectation.values, question: check.question },
  };
}

/** "New check: “…”" / "Changed check: “…”" for the pending sheet. */
export function pendingCheckLine(check: PendingOwnerCheck, words: Words): SentenceWithUserValues {
  return {
    text: check.action === "added" ? words.t("updates.pending.added") : words.t("updates.pending.changed"),
    values: { question: check.question },
  };
}

/** Whether something is still not with customers: a change, one of the owner's checks or a draft. */
export function hasPendingWork(view: Pick<PendingChangesView, "count" | "owner_checks" | "drafts"> | null | undefined): boolean {
  return Boolean(view && (view.count > 0 || (view.owner_checks?.length ?? 0) > 0 || (view.drafts?.length ?? 0) > 0));
}

/** Results of a run that did not pass. */
function problems(results: readonly AutotestScenarioResult[]): AutotestScenarioResult[] {
  return results.filter((result) => result.outcome !== "passed");
}

/** A run's owner-check result as a named failure (null for other scenarios or a check the run did not keep). */
export function namedFailureOf(result: AutotestScenarioResult): NamedFailure | null {
  const asked = result.owner_check;
  if (result.kind !== "owner_check" || !asked) {
    return null;
  }
  const answer = result.transcript.find((line) => line.author === "assistant")?.text ?? null;
  return {
    question: asked.question,
    expectation: asked.expectation,
    expected_text: asked.expected_text ?? null,
    checkId: result.autotest_case_id ?? null,
    conversationId: result.conversation_id ?? null,
    answerMessageId: result.answer_message_id ?? null,
    answer,
    reason: null,
  };
}

/**
 * The owner's checks a run did not pass, when they are the only problems
 * of the run (else an empty list: the run failed for other reasons too,
 * and the version page lists them all).
 */
export function onlyOwnerCheckFailures(results: readonly AutotestScenarioResult[]): NamedFailure[] {
  const failed = problems(results);
  if (failed.length === 0 || failed.some((result) => result.kind !== "owner_check")) {
    return [];
  }
  return failed.flatMap((result) => {
    const named = namedFailureOf(result);
    return named ? [named] : [];
  });
}

/** An apply's or "Check now"'s outcome as a named failure. */
export function namedFailureOfOutcome(outcome: OwnerCheckOutcome): NamedFailure {
  return {
    question: outcome.question,
    expectation: outcome.expectation,
    expected_text: outcome.expected_text ?? null,
    checkId: outcome.autotest_case_id,
    conversationId: outcome.conversation_id ?? null,
    answerMessageId: outcome.answer_message_id ?? null,
    answer: outcome.answer ?? null,
    reason: outcome.reason ?? null,
  };
}

/** The anchor of a check in "My checks" ("#check-…"), which the page scrolls to and marks. */
export function checkAnchor(checkId: string): string {
  return `check-${checkId}`;
}

/** "My checks" opened on one check. */
export function checkPath(businessId: string, checkId: string | null): string {
  const page = businessPath(businessId, "assistant/checks");
  return checkId ? `${page}#${checkAnchor(checkId)}` : page;
}

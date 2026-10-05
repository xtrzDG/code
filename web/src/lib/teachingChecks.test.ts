import { describe, expect, it } from "vitest";

import type { AnswerToImprove, CheckView, CorrectionResult } from "./teaching";
import {
  AUTO_LANGUAGE,
  checkBody,
  checkChanges,
  checkFormFromCorrection,
  checkFormFromItem,
  checkFormFromRating,
  checkFormOf,
  checkProblems,
  checkResultReasons,
  checkResultTone,
  needsExpectedText,
  newCheckForm,
  type CheckForm,
} from "./teachingChecks";

const CAKE = "Можно прийти со своим тортом?";

function check(changes: Partial<CheckView> = {}): CheckView {
  return {
    id: "case-1",
    created_at: 1,
    question: CAKE,
    expectation: "must_mention",
    expected_text: "торт",
    language: "ru",
    is_active: true,
    source: "owner",
    ...changes,
  };
}

function result(outcome: "passed" | "failed" | "errored", codes: NonNullable<CheckView["last_result"]>["check_codes"] = []) {
  return { outcome, assistant_version_number: 4, checked_at: 2, run_id: "run-1", check_codes: codes };
}

function correction(price: number | null): CorrectionResult {
  return {
    conversation_id: "conversation-1",
    message_id: "message-1",
    is_new: true,
    language: "ru",
    question: CAKE,
    item: { knowledge_item_id: "item-1", kind: "menu_item", title: "Торт", price_minor: price },
  };
}

function item(changes: Partial<AnswerToImprove>): AnswerToImprove {
  return { kind: "bad_rating", at: 1, ...changes };
}

describe("the choices of a check", () => {
  it("asks for words only when the answer must (not) mention them", () => {
    expect(needsExpectedText("must_mention")).toBe(true);
    expect(needsExpectedText("must_not_mention")).toBe(true);
    expect(needsExpectedText("must_hand_off")).toBe(false);
    expect(needsExpectedText("must_create_lead")).toBe(false);
  });

  it("starts empty, written by the owner, in the business's language", () => {
    expect(newCheckForm("ka")).toMatchObject({ question: "", expectation: "must_mention", language: "ka", source: "owner" });
  });

  it("opens a stored check as it is", () => {
    expect(checkFormOf(check({ source: "correction", source_conversation_id: "conversation-1" }))).toEqual({
      question: CAKE,
      expectation: "must_mention",
      expectedText: "торт",
      language: "ru",
      source: "correction",
      sourceConversationId: "conversation-1",
      sourceMessageId: null,
      sourceQuestionId: null,
    });
    expect(checkFormOf(check({ expectation: "must_hand_off", expected_text: null })).expectedText).toBe("");
  });
});

describe("a check saved from somewhere", () => {
  it("asks the corrected question and wants the new price in the answer", () => {
    expect(checkFormFromCorrection(correction(1850), "GEL")).toMatchObject({
      question: CAKE,
      expectedText: "18.5",
      language: "ru",
      source: "correction",
      sourceConversationId: "conversation-1",
      sourceMessageId: "message-1",
    });
    expect(checkFormFromCorrection(correction(null), "GEL").expectedText).toBe("");
  });

  it("from a question without an answer asks it in its language", () => {
    const question = item({ kind: "unanswered_question", question: CAKE, question_id: "question-1", language: "ru" });
    expect(checkFormFromItem(question, "ka")).toMatchObject({
      question: CAKE,
      expectation: "must_mention",
      language: "ru",
      source: "unanswered_question",
      sourceConversationId: null,
      sourceQuestionId: "question-1",
    });
  });

  it("from a bad rating asks the customer's words and wants a person when one was needed", () => {
    const rated = item({
      customer_message: CAKE,
      conversation_id: "conversation-1",
      message_id: "message-2",
      rating_reason: "should_hand_off",
    });
    expect(checkFormFromItem(rated, "ka")).toMatchObject({
      question: CAKE,
      expectation: "must_hand_off",
      language: "ka",
      source: "bad_rating",
      sourceMessageId: "message-2",
    });
    expect(checkFormFromItem(item({}), "ka").question).toBe("");
  });
});

describe("a check saved from a conversation rated bad", () => {
  const messages = [
    { id: "m1", author: "customer", text: "Здравствуйте" },
    { id: "m2", author: "assistant", text: "Здравствуйте!" },
    { id: "m3", author: "customer", text: ` ${CAKE} ` },
    { id: "m4", author: "assistant", text: "Нет." },
    { id: "m5", author: "customer", text: "Жаль" },
  ];

  it("asks what the customer wrote before the rated answer", () => {
    const form = checkFormFromRating(messages, { id: "conversation-1", language: "ru" }, "m4", "ka");
    expect(form).toMatchObject({ question: CAKE, language: "ru", source: "bad_rating", sourceMessageId: "m4" });
  });

  it("takes the customer's last words without a rated answer, or an unknown one", () => {
    expect(checkFormFromRating(messages, { id: "conversation-1" }, null, "ka")).toMatchObject({
      question: "Жаль",
      language: "ka",
    });
    expect(checkFormFromRating(messages, { id: "conversation-1" }, "gone", "ka").question).toBe("Жаль");
  });

  it("wants a person when the answer should have passed it on", () => {
    const form = checkFormFromRating(messages, { id: "c", rating_reason: "should_hand_off" }, "m2", "ru");
    expect(form.expectation).toBe("must_hand_off");
    expect(form.question).toBe("Здравствуйте");
    expect(checkFormFromRating([], { id: "c" }, null, "ru").question).toBe("");
  });
});

describe("what a check needs before it is sent", () => {
  const filled: CheckForm = { ...newCheckForm("ru"), question: CAKE, expectedText: "торт" };

  it("is a question, and words with a letter or digit when it checks a mention", () => {
    expect(checkProblems(filled)).toEqual([]);
    expect(checkProblems({ ...filled, question: "  ", expectedText: "?!" })).toEqual(["question", "expectedText"]);
    expect(checkProblems({ ...filled, expectedText: "15" })).toEqual([]);
    expect(checkProblems({ ...filled, expectation: "must_hand_off", expectedText: "" })).toEqual([]);
  });

  it("sends the words only when they matter", () => {
    expect(checkBody({ ...filled, question: ` ${CAKE} `, expectedText: " торт " })).toEqual({
      question: CAKE,
      expectation: "must_mention",
      expected_text: "торт",
      language: "ru",
      source: "owner",
      source_conversation_id: null,
      source_message_id: null,
      source_question_id: null,
    });
    expect(checkBody({ ...filled, expectation: "must_create_lead" }).expected_text).toBeNull();
    expect(checkChanges({ ...filled, expectedText: " торт " })).toEqual({
      question: CAKE,
      expectation: "must_mention",
      expected_text: "торт",
      language: "ru",
    });
    expect(checkChanges({ ...filled, expectation: "must_hand_off" }).expected_text).toBeNull();
  });

  it("leaves a new check's language to its question unless the owner picks one", () => {
    expect(checkBody({ ...filled, language: AUTO_LANGUAGE }).language).toBeNull();
    expect(newCheckForm(AUTO_LANGUAGE).language).toBe(AUTO_LANGUAGE);
  });
});

describe("the latest result of a check", () => {
  it("reads by its outcome", () => {
    expect(checkResultTone(check())).toBe("neutral");
    expect(checkResultTone(check({ last_result: null }))).toBe("neutral");
    expect(checkResultTone(check({ last_result: result("passed") }))).toBe("success");
    expect(checkResultTone(check({ last_result: result("failed") }))).toBe("danger");
    expect(checkResultTone(check({ last_result: result("errored") }))).toBe("warning");
  });

  it("names the reasons the owner can act on and leaves the rest to the outcome", () => {
    const failed = check({ last_result: result("failed", ["expected_text_missing", "judge_unavailable", "not_handed_off"]) });
    expect(checkResultReasons(failed)).toEqual(["teaching.checks.codes.expected_text_missing", "teaching.checks.codes.not_handed_off"]);
    expect(checkResultReasons(check())).toEqual([]);
    expect(checkResultReasons(check({ last_result: { ...result("passed"), check_codes: undefined } }))).toEqual([]);
  });
});

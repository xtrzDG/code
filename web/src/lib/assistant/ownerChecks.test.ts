import { describe, expect, it } from "vitest";

import { en } from "@/i18n/messages/en";
import { ka } from "@/i18n/messages/ka";
import { ru } from "@/i18n/messages/ru";
import { createTranslator } from "@/i18n/translate";

import type { AutotestScenarioResult } from "./autotests";
import {
  checkAnchor,
  checkPath,
  expectationSentence,
  failureSentence,
  hasPendingWork,
  namedFailureOfOutcome,
  onlyOwnerCheckFailures,
  pendingCheckLine,
  type OwnerCheckOutcome,
} from "./ownerChecks";

const english = createTranslator("en", en);
const russian = createTranslator("ru", ru, en);
const georgian = createTranslator("ka", ka, en);

const DOG = "Можно прийти с собакой?";

function result(overrides: Partial<AutotestScenarioResult>): AutotestScenarioResult {
  return {
    scenario_key: "booking-ru",
    kind: "booking",
    language: "ru",
    outcome: "passed",
    scores: [],
    check_notes: [],
    judge_notes: [],
    transcript: [],
    cost_micro_usd: 0,
    ...overrides,
  };
}

const failedDogCheck = result({
  scenario_key: "owner_check-case_1-ru",
  kind: "owner_check",
  outcome: "failed",
  autotest_case_id: "case_1",
  conversation_id: "conv_1",
  answer_message_id: "msg_2",
  owner_check: { question: DOG, expectation: "must_hand_off", expected_text: null },
  transcript: [
    { author: "customer", text: DOG },
    { author: "assistant", text: "Да, конечно!" },
  ],
});

describe("the owner's checks in the story of an update", () => {
  it("say what the answer must do in each language, with the words when there are any", () => {
    expect(expectationSentence({ expectation: "must_hand_off" }, russian)).toBe("ответ должен передать человеку");
    expect(expectationSentence({ expectation: "must_mention", expected_text: " 20 лари " }, russian)).toBe(
      "ответ должен упомянуть «20 лари»",
    );
    expect(expectationSentence({ expectation: "must_not_mention", expected_text: "free" }, english)).toBe(
      "the answer must not mention “free”",
    );
    expect(expectationSentence({ expectation: "must_create_lead" }, georgian)).toBe("პასუხმა მოთხოვნა უნდა მიიღოს");
  });

  it("name a failed check by its question, never as a bare “Your check”", () => {
    const [named] = onlyOwnerCheckFailures([result({}), failedDogCheck]);
    expect(named).toMatchObject({ question: DOG, checkId: "case_1", conversationId: "conv_1", answerMessageId: "msg_2", answer: "Да, конечно!" });
    expect(failureSentence(named!, russian)).toBe(`Не прошла ваша проверка: «${DOG}» — ответ должен передать человеку`);
  });

  it("speak for the owner's checks only when nothing else failed", () => {
    expect(onlyOwnerCheckFailures([failedDogCheck, result({ outcome: "failed" })])).toEqual([]);
    expect(onlyOwnerCheckFailures([result({}), result({ kind: "human_request" })])).toEqual([]);
    // A result kept before runs knew what the check asked is not guessed at.
    expect(onlyOwnerCheckFailures([{ ...failedDogCheck, owner_check: null }])).toEqual([]);
    expect(onlyOwnerCheckFailures([{ ...failedDogCheck, outcome: "errored" }])).toHaveLength(1);
  });

  it("keep the reason and the answer of an apply's or Check now's outcome", () => {
    const outcome: OwnerCheckOutcome = {
      autotest_case_id: "case_2",
      question: "Do you have vegan food?",
      expectation: "must_mention",
      expected_text: "vegan",
      outcome: "failed",
      reason: "The answer did not mention “vegan”.",
      answer: "We have khachapuri.",
      conversation_id: "conv_9",
      answer_message_id: null,
      checked_at: 1,
    };
    expect(namedFailureOfOutcome(outcome)).toEqual({
      question: "Do you have vegan food?",
      expectation: "must_mention",
      expected_text: "vegan",
      checkId: "case_2",
      conversationId: "conv_9",
      answerMessageId: null,
      answer: "We have khachapuri.",
      reason: "The answer did not mention “vegan”.",
    });
  });

  it("list new and changed checks among the pending changes", () => {
    const added = { autotest_case_id: "c", action: "added", question: DOG, expectation: "must_hand_off", language: "ru" } as const;
    expect(pendingCheckLine(added, russian)).toBe(`Новая проверка: «${DOG}»`);
    expect(pendingCheckLine({ ...added, action: "changed" }, english)).toBe(`Changed check: “${DOG}”`);
  });

  it("never call everything live while a change, a check or a draft is pending", () => {
    expect(hasPendingWork(null)).toBe(false);
    expect(hasPendingWork({ count: 0, owner_checks: [], drafts: [] })).toBe(false);
    expect(hasPendingWork({ count: 1 })).toBe(true);
    expect(
      hasPendingWork({
        count: 0,
        drafts: [{ assistant_version_id: "v3", version_number: 3, status: "ready", created_at: 1 }],
      }),
    ).toBe(true);
    expect(
      hasPendingWork({
        count: 0,
        owner_checks: [{ autotest_case_id: "c", action: "added", question: DOG, expectation: "must_hand_off", language: "ru" }],
      }),
    ).toBe(true);
  });

  it("open My checks on the check", () => {
    expect(checkAnchor("case_1")).toBe("check-case_1");
    expect(checkPath("biz_1", "case_1")).toBe("/b/biz_1/assistant/checks#check-case_1");
    expect(checkPath("biz_1", null)).toBe("/b/biz_1/assistant/checks");
  });
});

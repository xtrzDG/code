import { describe, expect, it } from "vitest";

import type { KnowledgeItemDetails, WizardQuestionView } from "@/api/types";

import { answersPayload, initialAnswers, isChoiceQuestion, validateAnswers } from "./answers";
import {
  faqPayload,
  faqRowFromItem,
  isFaqRowChanged,
  markFaqRowsSaved,
  newFaqRow,
  validateFaqRow,
} from "./faq";

function question(
  key: string,
  answerType: WizardQuestionView["question"]["answer_type"],
  answer: string | null = null,
  selected: string[] | null = [],
): WizardQuestionView {
  return {
    question: {
      key,
      fact_key: key,
      step: "offer",
      answer_type: answerType,
      is_required: false,
      label: key,
      choices: [],
    },
    answer,
    selected_choice_keys: selected,
  } as WizardQuestionView;
}

function faqItem(overrides: Partial<KnowledgeItemDetails> = {}): KnowledgeItemDetails {
  return {
    id: "knowledge_item_faq",
    business_id: "business_1",
    kind: "faq",
    title: "Do you have parking?",
    body: "Yes, behind the building.",
    price_minor: null,
    currency_code: null,
    duration_minutes: null,
    tags: [],
    attributes: [],
    languages: ["en"],
    source: "profile",
    is_active: true,
    created_at: 0,
    updated_at: 0,
    ...overrides,
  };
}

describe("wizard answers", () => {
  it("read old comma-separated choice answers and fall back to a selected key", () => {
    const values = initialAnswers([
      question("diet", "single_choice", "vegan,halal", []),
      question("kids", "yes_no", null, ["yes"]),
      question("note", "long_text", null, null),
    ]);

    expect(values.diet).toEqual({ text: "", choices: ["vegan", "halal"] });
    expect(values.kids).toEqual({ text: "yes", choices: [] });
    expect(values.note).toEqual({ text: "", choices: [] });
    expect(isChoiceQuestion(question("diet", "multiple_choice"))).toBe(true);
  });

  it("leave out questions without a value and empty choices", () => {
    const questions = [question("diet", "multiple_choice"), question("seats", "number")];

    expect(answersPayload(questions, { diet: { text: "", choices: [] } })).toEqual([]);
  });

  it("limit short and long texts and accept valid links", () => {
    const questions = [
      question("site", "url"),
      question("tagline", "short_text"),
      question("story", "long_text"),
      question("kids", "yes_no"),
    ];
    const values = {
      site: { text: "https://example.com/menu", choices: [] },
      tagline: { text: "x".repeat(301), choices: [] },
      story: { text: "y".repeat(4001), choices: [] },
      kids: { text: "yes", choices: [] },
    };

    expect(validateAnswers(questions, values)).toEqual({
      tagline: "validation.tooLong",
      story: "validation.tooLong",
    });
    expect(
      validateAnswers(questions, {
        tagline: { text: "x".repeat(300), choices: [] },
        story: { text: "y".repeat(4000), choices: [] },
      }),
    ).toEqual({});
  });
});

describe("FAQ rows", () => {
  it("start unchanged from a saved item and change when edited", () => {
    const row = faqRowFromItem(faqItem({ body: null, languages: null }));

    expect(row).toMatchObject({ id: "knowledge_item_faq", answer: "", languages: [] });
    expect(isFaqRowChanged(row)).toBe(false);
    expect(isFaqRowChanged({ ...row, answer: "Yes" })).toBe(true);
    expect(isFaqRowChanged({ ...row, question: `  ${row.question}  ` })).toBe(false);
  });

  it("require both halves once either is filled", () => {
    expect(validateFaqRow(newFaqRow("a"))).toEqual({});
    expect(validateFaqRow({ ...newFaqRow("b"), question: "Parking?" })).toEqual({
      answer: "validation.required",
    });
    expect(validateFaqRow({ ...newFaqRow("c"), answer: "Yes" })).toEqual({
      question: "validation.required",
    });
  });

  it("send the id of edited saved rows and skip unchanged ones", () => {
    const saved = faqRowFromItem(faqItem());
    const edited = { ...saved, answer: " Free for guests. " };

    expect(faqPayload([saved, edited])).toEqual([
      {
        id: "knowledge_item_faq",
        question: "Do you have parking?",
        answer: "Free for guests.",
        languages: ["en"],
      },
    ]);
  });

  it("match saved items by id or by question and keep the rest", () => {
    const byQuestion = { ...newFaqRow("new"), question: "do you have PARKING? ", answer: "Yes" };
    const byId = {
      ...faqRowFromItem(faqItem({ id: "knowledge_item_2", title: "Opening hours?" })),
      answer: "Changed",
    };
    const unmatched = { ...newFaqRow("other"), question: "Wifi?", answer: "Yes" };
    const blank = newFaqRow("blank");

    const rows = markFaqRowsSaved(
      [byQuestion, byId, unmatched, blank],
      [faqItem(), faqItem({ id: "knowledge_item_2", title: "Other" }), faqItem({ kind: "rule", title: "Wifi?" })],
    );

    expect(rows[0]).toMatchObject({ id: "knowledge_item_faq" });
    expect(isFaqRowChanged(rows[0])).toBe(false);
    expect(rows[1]).toMatchObject({ id: "knowledge_item_2" });
    expect(isFaqRowChanged(rows[1])).toBe(false);
    expect(rows[2]).toBe(unmatched);
    expect(rows[3]).toBe(blank);
  });
});

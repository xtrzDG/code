import { describe, expect, it } from "vitest";

import type { KnowledgeItemDetails, WizardQuestionView } from "@/api/types";

import { answersPayload, initialAnswers, validateAnswers } from "./answers";
import { cleanRules, faqPayload, newFaqRow } from "./faq";
import {
  isOfferRowChanged,
  markOfferRowsSaved,
  newOfferRow,
  offerItemsPayload,
  offerKinds,
  offerRowFromItem,
  validateOfferRow,
} from "./offers";

function question(key: string, answerType: WizardQuestionView["question"]["answer_type"], answer?: string, selected: string[] = []): WizardQuestionView {
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
    answer: answer ?? null,
    selected_choice_keys: selected,
  };
}

function item(overrides: Partial<KnowledgeItemDetails>): KnowledgeItemDetails {
  return {
    id: "knowledge_item_1",
    business_id: "business_1",
    kind: "menu_item",
    title: "Khachapuri",
    body: null,
    price_minor: 1850,
    currency_code: "GEL",
    duration_minutes: null,
    tags: ["vegetarian"],
    attributes: [],
    languages: [],
    source: "profile",
    is_active: true,
    created_at: 0,
    updated_at: 0,
    ...overrides,
  };
}

describe("niche answers", () => {
  const questions = [
    question("cuisine", "short_text", "Georgian"),
    question("diet", "multiple_choice", "vegan,halal", ["vegan", "halal"]),
    question("kids", "yes_no", "yes", ["yes"]),
    question("seats", "number"),
  ];

  it("start from the current answers", () => {
    expect(initialAnswers(questions)).toEqual({
      cuisine: { text: "Georgian", choices: [] },
      diet: { text: "", choices: ["vegan", "halal"] },
      kids: { text: "yes", choices: [] },
      seats: { text: "", choices: [] },
    });
  });

  it("send answered questions only (the rest are cleared)", () => {
    const values = initialAnswers(questions);
    values.seats = { text: " 40 ", choices: [] };
    values.cuisine = { text: "  ", choices: [] };
    expect(answersPayload(questions, values)).toEqual([
      { question_key: "diet", choice_keys: ["vegan", "halal"] },
      { question_key: "kids", answer: "yes" },
      { question_key: "seats", answer: "40" },
    ]);
  });

  it("catch numbers and links the API would refuse", () => {
    const linkQuestion = question("site", "url");
    expect(
      validateAnswers([questions[3]!, linkQuestion], {
        seats: { text: "forty", choices: [] },
        site: { text: "example.com", choices: [] },
      }),
    ).toEqual({ seats: "validation.wholeNumber", site: "validation.url" });
  });
});

describe("offer rows", () => {
  it("keep the niche's selling kinds", () => {
    expect(offerKinds(["menu_item", "package", "faq", "policy"])).toEqual(["menu_item", "package"]);
    expect(offerKinds(["faq"])).toEqual(["service"]);
  });

  it("show prices in major units and send only edited rows", () => {
    const row = offerRowFromItem(item({}), "GEL");
    expect(row.price).toBe("18.5");
    expect(isOfferRowChanged(row)).toBe(false);
    expect(offerItemsPayload([row], "GEL")).toEqual([]);

    const edited = { ...row, price: "19,90" };
    expect(offerItemsPayload([edited], "GEL")).toEqual([
      {
        id: "knowledge_item_1",
        kind: "menu_item",
        title: "Khachapuri",
        body: null,
        price_minor: 1990,
        duration_minutes: null,
        tags: ["vegetarian"],
        attributes: [],
        languages: [],
        is_active: true,
      },
    ]);
  });

  it("skip blank new rows and validate filled ones", () => {
    const blank = newOfferRow("service", "new-1");
    expect(offerItemsPayload([blank], "GEL")).toEqual([]);
    expect(validateOfferRow(blank, "GEL")).toEqual({});
    expect(validateOfferRow({ ...blank, price: "abc" }, "GEL")).toEqual({ title: "validation.required", price: "validation.number" });
    expect(validateOfferRow({ ...blank, title: "Massage", duration: "0" }, "GEL")).toEqual({ duration: "validation.positive" });
  });

  it("refuse prices that would be stored at the wrong amount", () => {
    const row = { ...newOfferRow("service", "new-1"), title: "Massage" };
    expect(validateOfferRow({ ...row, price: "1,200" }, "USD").price).toBe("knowledge.form.priceAmbiguous");
    expect(validateOfferRow({ ...row, price: "25.000" }, "IDR").price).toBe("knowledge.form.priceAmbiguous");
    expect(validateOfferRow({ ...row, price: "1200,5" }, "JPY").price).toBe("knowledge.form.priceTooPrecise");
    expect(validateOfferRow({ ...row, price: "1200" }, "USD")).toEqual({});
    expect(validateOfferRow({ ...row, price: "1,200" }, "JPY")).toEqual({});
    expect(offerItemsPayload([{ ...row, price: "1,200" }], "JPY")[0]?.price_minor).toBe(1200);
  });

  it("take the saved ids and become unchanged after a save", () => {
    const fresh = { ...newOfferRow("service", "new-1"), title: "Massage", price: "50" };
    const [saved] = markOfferRowsSaved([fresh], [item({ id: "knowledge_item_9", kind: "service", title: "massage" })]);
    expect(saved?.id).toBe("knowledge_item_9");
    expect(saved && isOfferRowChanged(saved)).toBe(false);
  });
});

describe("FAQ and rules", () => {
  it("send complete new questions", () => {
    const row = { ...newFaqRow("new-1"), question: " Parking? ", answer: "Yes " };
    expect(faqPayload([row, newFaqRow("new-2")])).toEqual([{ question: "Parking?", answer: "Yes", languages: [] }]);
  });

  it("drop blank and repeated rules", () => {
    expect(cleanRules([" Complaint ", "", "complaint", "Banquet over 20"])).toEqual(["Complaint", "Banquet over 20"]);
  });
});

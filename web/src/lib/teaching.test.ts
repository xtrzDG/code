import { describe, expect, it } from "vitest";

import {
  correctionBody,
  correctionFormOf,
  correctionProblems,
  guardChip,
  guardReasonKeys,
  isPriceScope,
  latestAnswerId,
  type CorrectionDraft,
  type CorrectionForm,
} from "./teaching";

const CAKE = "Можно прийти со своим тортом?";

function draft(changes: Partial<CorrectionDraft> = {}): CorrectionDraft {
  return {
    answer: "Да, конечно.",
    conversation_id: "conversation-1",
    message_id: "message-1",
    question: CAKE,
    is_corrected: false,
    suggested_scope: "faq",
    ...changes,
  };
}

function form(changes: Partial<CorrectionForm> = {}): CorrectionForm {
  return { scope: "faq", question: CAKE, answer: "Свой торт можно, без платы.", itemId: null, price: "", ...changes };
}

const PRICED_FACT = {
  knowledge_item_id: "item-7",
  kind: "menu_item" as const,
  title: "Торт",
  price_minor: 1500,
  currency_code: "GEL",
};

describe("the reply guard's chip on an answer", () => {
  it("is nothing for a clean answer, an answer without a verdict or no guard at all", () => {
    expect(guardChip(null)).toBeNull();
    expect(guardChip(undefined)).toBeNull();
    expect(guardChip({})).toBeNull();
    expect(guardChip({ verdict: "clean" })).toBeNull();
  });

  it("warns about a rewritten answer and names why", () => {
    expect(guardChip({ verdict: "rewritten", reasons: ["unverified_values"] })).toEqual({
      tone: "warning",
      label: "teaching.guard.rewritten",
      reasons: ["teaching.guard.reasons.unverified_values"],
    });
  });

  it("is red for an answer held back and passed to a person", () => {
    expect(guardChip({ verdict: "handed_off" })).toEqual({
      tone: "danger",
      label: "teaching.guard.handed_off",
      reasons: [],
    });
  });

  it("puts every reason into words", () => {
    expect(guardReasonKeys(["unsupported_claims", "personal_data"])).toEqual([
      "teaching.guard.reasons.unsupported_claims",
      "teaching.guard.reasons.personal_data",
    ]);
    expect(guardReasonKeys(null)).toEqual([]);
    expect(guardReasonKeys(undefined)).toEqual([]);
  });
});

describe("the newest answer of the assistant", () => {
  it("is the last assistant message, whatever follows it", () => {
    const messages = [
      { id: "a", author: "customer" },
      { id: "b", author: "assistant" },
      { id: "c", author: "customer" },
      { id: "d", author: "assistant" },
      { id: "e", author: "staff" },
    ];
    expect(latestAnswerId(messages)).toBe("d");
  });

  it("is null when the assistant has not answered", () => {
    expect(latestAnswerId([{ id: "a", author: "customer" }])).toBeNull();
    expect(latestAnswerId([])).toBeNull();
  });
});

describe("the form of Fix this answer", () => {
  it("opens with the customer's question and the suggested kind", () => {
    expect(correctionFormOf(draft())).toEqual(form({ answer: "" }));
    expect(isPriceScope("price")).toBe(true);
    expect(isPriceScope("rule")).toBe(false);
  });

  it("opens empty without a question", () => {
    expect(correctionFormOf(draft({ question: null })).question).toBe("");
  });

  it("keeps the corrected answer when the answer was fixed before", () => {
    const fixed = draft({
      is_corrected: true,
      current_fact: { knowledge_item_id: "item-1", kind: "faq", title: CAKE, body: "Свой торт можно." },
    });
    expect(correctionFormOf(fixed).answer).toBe("Свой торт можно.");
    expect(correctionFormOf(draft({ is_corrected: true })).answer).toBe("");
  });

  it("reprices the current priced item when the price is suggested", () => {
    const priced = correctionFormOf(draft({ suggested_scope: "price", current_fact: PRICED_FACT }));
    expect(priced.itemId).toBe("item-7");
    expect(priced.scope).toBe("price");
    const unpriced = correctionFormOf(
      draft({ suggested_scope: "price", current_fact: { ...PRICED_FACT, price_minor: null } }),
    );
    expect(unpriced.itemId).toBeNull();
    expect(correctionFormOf(draft({ current_fact: PRICED_FACT })).itemId).toBeNull();
  });
});

describe("what Fix this answer needs before it is sent", () => {
  it("is a question and an answer for a written fact", () => {
    expect(correctionProblems(form(), "GEL")).toEqual([]);
    expect(correctionProblems(form({ question: " ", answer: "" }), "GEL")).toEqual(["question", "answer"]);
    expect(correctionProblems(form({ scope: "rule", answer: "  " }), "GEL")).toEqual(["answer"]);
  });

  it("is a price, and a name for a new item", () => {
    expect(correctionProblems(form({ scope: "price", price: "15" }), "GEL")).toEqual([]);
    expect(correctionProblems(form({ scope: "price", question: "", price: "" }), "GEL")).toEqual([
      "question",
      "price",
    ]);
    expect(correctionProblems(form({ scope: "price", question: "", itemId: "item-7", price: "15" }), "GEL")).toEqual(
      [],
    );
  });

  it("refuses a price that is not one", () => {
    expect(correctionProblems(form({ scope: "price", price: "abc" }), "GEL")).toEqual(["number"]);
    expect(correctionProblems(form({ scope: "price", price: "1.5055" }), "GEL")).toEqual(["precision"]);
  });
});

describe("the body of a correction", () => {
  it("sends a written fact trimmed", () => {
    expect(correctionBody(form({ question: ` ${CAKE} `, answer: " Можно. " }), "GEL")).toEqual({
      scope: "faq",
      question: CAKE,
      correct_answer: "Можно.",
    });
  });

  it("reprices an item without renaming it", () => {
    expect(correctionBody(form({ scope: "price", itemId: "item-7", answer: "", price: "18,5" }), "GEL")).toEqual({
      scope: "price",
      knowledge_item_id: "item-7",
      question: null,
      correct_answer: null,
      price_minor: 1850,
    });
  });

  it("names a new priced item with its description", () => {
    expect(correctionBody(form({ scope: "price", question: "Торт ", answer: "Целый", price: "15" }), "GEL")).toEqual({
      scope: "price",
      knowledge_item_id: null,
      question: "Торт",
      correct_answer: "Целый",
      price_minor: 1500,
    });
  });

  it("sends nothing for a price that is not a number (the form refuses it first)", () => {
    expect(correctionBody(form({ scope: "price", price: "abc" }), "GEL").price_minor).toBe(0);
  });
});

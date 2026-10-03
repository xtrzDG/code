import { describe, expect, it } from "vitest";

import type { KnowledgeItemDetails, Schema } from "@/api/types";

import {
  blankOfferRow,
  editOfferRow,
  initialOfferRows,
  isOfferItem,
  offerSave,
  pricedCount,
  savedOfferRow,
} from "./offer";

function item(overrides: Partial<KnowledgeItemDetails>): KnowledgeItemDetails {
  return {
    id: "knowledge_1",
    business_id: "business_1",
    kind: "service",
    title: "Women's haircut",
    price_minor: 4500,
    currency_code: "EUR",
    duration_minutes: 60,
    is_active: true,
    tags: [],
    attributes: [],
    languages: [],
    created_at: 1,
    updated_at: 1,
    ...overrides,
  } as KnowledgeItemDetails;
}

const EXAMPLES: Schema<"StarterOfferView">[] = [
  { key: "haircut", kind: "service", title: "Women's haircut", duration_minutes: 60 },
  { key: "manicure", kind: "service", title: "Manicure", duration_minutes: null },
];

describe("offer rows", () => {
  it("start with saved offers, then examples not there yet", () => {
    const rows = initialOfferRows([item({}), item({ id: "faq_1", kind: "faq", title: "Parking?" })], EXAMPLES, "EUR");
    expect(rows.map((row) => [row.title, row.price, row.isSuggestion])).toEqual([
      ["Women's haircut", "45", false],
      ["Manicure", "", true],
    ]);
    expect(rows[1]?.duration).toBe("");
    expect(initialOfferRows([], EXAMPLES, "EUR")[0]?.duration).toBe("60");
  });

  it("leave switched-off items and questions off the table", () => {
    expect(isOfferItem({ kind: "service", is_active: true })).toBe(true);
    expect(isOfferItem({ kind: "service", is_active: false })).toBe(false);
    expect(isOfferItem({ kind: "policy", is_active: true })).toBe(false);
  });

  it("never save an untouched example", () => {
    const [, suggestion] = initialOfferRows([item({})], EXAMPLES, "EUR");
    if (!suggestion) {
      throw new Error("no suggestion");
    }
    expect(offerSave(suggestion, "EUR")).toEqual({ kind: "none" });
    const priced = editOfferRow(suggestion, { price: "30" });
    expect(priced.isSuggestion).toBe(false);
    expect(offerSave(priced, "EUR")).toEqual({
      kind: "create",
      body: { kind: "service", title: "Manicure", price_minor: 3000, duration_minutes: null, is_active: true },
    });
  });

  it("save a changed saved row as an update, an unchanged one not at all", () => {
    const [saved] = initialOfferRows([item({})], [], "EUR");
    if (!saved) {
      throw new Error("no row");
    }
    expect(offerSave(saved, "EUR")).toEqual({ kind: "none" });
    expect(offerSave(editOfferRow(saved, { price: "50.5" }), "EUR")).toEqual({
      kind: "update",
      id: "knowledge_1",
      body: { kind: "service", title: "Women's haircut", price_minor: 5050, duration_minutes: 60 },
    });
  });

  it("wait with rows that are blank or invalid", () => {
    expect(offerSave(blankOfferRow("service", "new-1"), "EUR")).toEqual({ kind: "none" });
    expect(offerSave(editOfferRow(blankOfferRow("service", "new-1"), { title: "Pedicure", price: "abc" }), "EUR")).toEqual({
      kind: "invalid",
    });
  });

  it("take the stored id and baseline after a save", () => {
    const typed = editOfferRow(blankOfferRow("service", "new-1"), { title: "Pedicure", price: "25" });
    const stored = savedOfferRow(typed, item({ id: "knowledge_9", title: "Pedicure", price_minor: 2500, duration_minutes: null }), "EUR");
    expect(stored.id).toBe("knowledge_9");
    expect(offerSave(stored, "EUR")).toEqual({ kind: "none" });
  });

  it("stay changed when the owner typed on during the save", () => {
    const typed = editOfferRow(blankOfferRow("service", "new-1"), { title: "Pedicure", price: "27" });
    const stored = savedOfferRow(typed, item({ id: "knowledge_9", title: "Pedicure", price_minor: 2500, duration_minutes: null }), "EUR");
    expect(offerSave(stored, "EUR").kind).toBe("update");
  });

  it("count the rows with a name and a price", () => {
    const rows = [
      ...initialOfferRows([item({})], EXAMPLES, "EUR"),
      editOfferRow(blankOfferRow("service", "x"), { title: "Brows" }),
    ];
    expect(pricedCount(rows, "EUR")).toBe(1);
  });
});

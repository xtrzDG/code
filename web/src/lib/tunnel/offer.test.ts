import { describe, expect, it } from "vitest";

import type { KnowledgeItemDetails, Schema } from "@/api/types";

import {
  blankOfferRow,
  editOfferRow,
  initialOfferRows,
  isOfferItem,
  offerSave,
  pastedOfferRows,
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
  it("offer the niche's examples to an empty table, with their minutes", () => {
    const rows = initialOfferRows([item({ id: "faq_1", kind: "faq", title: "Parking?" })], EXAMPLES, "EUR");
    expect(rows.map((row) => [row.title, row.price, row.isSuggestion, row.key])).toEqual([
      ["Women's haircut", "", true, "starter-haircut"],
      ["Manicure", "", true, "starter-manicure"],
    ]);
    expect(rows[0]?.duration).toBe("60");
    expect(rows[1]?.duration).toBe("");
  });

  it("bring back no example once anything is saved, whatever its name or language", () => {
    const lunch: Schema<"StarterOfferView">[] = [{ key: "business_lunch", kind: "menu_item", title: "Business lunch", duration_minutes: null }];
    // Saved in Russian, reopened in English: "Бизнес-ланч" is not followed by "Business lunch".
    const rows = initialOfferRows([item({ kind: "menu_item", title: "Бизнес-ланч", price_minor: 1800 })], lunch, "EUR");
    expect(rows.map((row) => [row.title, row.isSuggestion])).toEqual([["Бизнес-ланч", false]]);
    // A saved line of another name hides the examples just as well.
    expect(initialOfferRows([item({ title: "Gel nails" })], EXAMPLES, "EUR").every((row) => !row.isSuggestion)).toBe(true);
  });

  it("bring back no example once the offer step was finished or skipped", () => {
    expect(initialOfferRows([], EXAMPLES, "EUR", { isStepCompleted: true })).toEqual([]);
  });

  it("keep the saved lines in the order they were added, though the API lists the newest first", () => {
    const rows = initialOfferRows(
      [
        item({ id: "knowledge_3", title: "Coloring", created_at: 30 }),
        item({ id: "knowledge_2", title: "Blow-dry", created_at: 20 }),
        item({ id: "knowledge_1", title: "Men's haircut", created_at: 10 }),
      ],
      [],
      "EUR",
    );
    expect(rows.map((row) => row.title)).toEqual(["Men's haircut", "Blow-dry", "Coloring"]);
  });

  it("do not bring back an example the owner removed, matched by its key", () => {
    const rows = initialOfferRows([], EXAMPLES, "EUR", { done: new Set(["manicure"]) });
    expect(rows.map((row) => [row.title, row.isSuggestion])).toEqual([["Women's haircut", true]]);
    expect(rows[0]?.key).toBe("starter-haircut");
    // The key, not the title: an example of the same name but another key stays.
    const renamed = initialOfferRows([], [{ ...EXAMPLES[1]!, key: "nails" }], "EUR", { done: new Set(["manicure"]) });
    expect(renamed.map((row) => row.title)).toEqual(["Manicure"]);
  });

  it("leave switched-off items and questions off the table", () => {
    expect(isOfferItem({ kind: "service", is_active: true })).toBe(true);
    expect(isOfferItem({ kind: "service", is_active: false })).toBe(false);
    expect(isOfferItem({ kind: "policy", is_active: true })).toBe(false);
  });

  it("never save an untouched example", () => {
    const [, suggestion] = initialOfferRows([], EXAMPLES, "EUR");
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

describe("rows of the profile editor's offer table", () => {
  it("drop the duration when the kind lasts no time", () => {
    const haircut = editOfferRow(blankOfferRow("service", "new-1"), { title: "Haircut", duration: "45" });
    expect(haircut.duration).toBe("45");
    expect(editOfferRow(haircut, { kind: "product" }).duration).toBe("");
    expect(editOfferRow(haircut, { kind: "package" }).duration).toBe("45");
  });

  it("come from pasted lines as the owner's own rows", () => {
    const rows = pastedOfferRows(
      [
        { title: "Lobio", price: "12", duration: "" },
        { title: "Supra", price: "90", duration: "180" },
      ],
      "menu_item",
      (index) => `paste-${index}`,
    );
    expect(rows.map((row) => [row.key, row.title, row.price, row.duration, row.isSuggestion])).toEqual([
      ["paste-0", "Lobio", "12", "", false],
      ["paste-1", "Supra", "90", "", false],
    ]);
    expect(offerSave(rows[0]!, "GEL")).toEqual({
      kind: "create",
      body: { kind: "menu_item", title: "Lobio", price_minor: 1200, duration_minutes: null, is_active: true },
    });
  });
});

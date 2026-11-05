import { describe, expect, it } from "vitest";

import type { KnowledgeItemDetails } from "@/api/types";

import { newFaqRow } from "../wizard/faq";
import { faqRowsFrom, faqSave, savedFaqRow } from "./faq";

function item(overrides: Partial<KnowledgeItemDetails>): KnowledgeItemDetails {
  return {
    id: "knowledge_1",
    business_id: "biz_1",
    kind: "faq",
    title: "Is there parking?",
    body: "Yes, in the yard.",
    is_active: true,
    created_at: 1,
    updated_at: 1,
    ...overrides,
  } as KnowledgeItemDetails;
}

describe("ready answers in the profile editor", () => {
  it("are the active answers, oldest first", () => {
    const rows = faqRowsFrom([
      item({ id: "k3", created_at: 3, title: "Wi-Fi?" }),
      item({ id: "k1", created_at: 1 }),
      item({ id: "k2", created_at: 2, is_active: false }),
      item({ id: "k4", created_at: 4, kind: "policy" }),
    ]);
    expect(rows.map((row) => row.id)).toEqual(["k1", "k3"]);
  });

  it("are saved once a line has both a question and an answer", () => {
    expect(faqSave(newFaqRow("new-1"))).toEqual({ kind: "none" });
    expect(faqSave({ ...newFaqRow("new-1"), question: "Do you deliver?" })).toEqual({ kind: "invalid" });
    expect(faqSave({ ...newFaqRow("new-1"), question: " Do you deliver? ", answer: " Yes, by Wolt. " })).toEqual({
      kind: "create",
      body: { kind: "faq", title: "Do you deliver?", body: "Yes, by Wolt.", is_active: true },
    });
    const [saved] = faqRowsFrom([item({})]);
    expect(faqSave(saved!)).toEqual({ kind: "none" });
    expect(faqSave({ ...saved!, answer: "Yes, for free." })).toEqual({
      kind: "update",
      id: "knowledge_1",
      body: { title: "Is there parking?", body: "Yes, for free." },
    });
  });

  it("take the stored text as the new baseline unless the owner typed on", () => {
    const typed = { ...newFaqRow("new-1"), question: "Do you deliver?", answer: "Yes." };
    const stored = item({ id: "k9", title: "Do you deliver?", body: "Yes." });
    expect(faqSave(savedFaqRow(typed, stored))).toEqual({ kind: "none" });
    const typedOn = { ...typed, answer: "Yes, by Wolt." };
    expect(savedFaqRow(typedOn, stored).id).toBe("k9");
    expect(faqSave(savedFaqRow(typedOn, stored))).toEqual({ kind: "update", id: "k9", body: { title: "Do you deliver?", body: "Yes, by Wolt." } });
  });
});

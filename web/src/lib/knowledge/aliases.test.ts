import { describe, expect, it } from "vitest";

import {
  acceptAlias,
  addAlias,
  aliasesInLanguages,
  aliasLanguages,
  aliasRowsFrom,
  countSuggested,
  MAX_ALIAS_LENGTH,
  mergeSuggestions,
  removeAlias,
  sameAliases,
  type AliasRow,
} from "./aliases";
import { emptyKnowledgeForm, knowledgeCreateBody, knowledgeFormFromItem, knowledgePatchBody } from "./form";

const georgian: AliasRow = { language: "ka", text: "იმერული ხაჭაპური", status: "approved" };
const russian: AliasRow = { language: "ru", text: "Хачапури по-имеретински", status: "suggested" };
const hebrew: AliasRow = { language: "he", text: "חצ'אפורי", status: "approved" };

describe("aliases: the item's names in the business's other languages", () => {
  it("copies the API's rows and reads a missing list as none", () => {
    const stored = [{ ...georgian, extra: true } as AliasRow];
    expect(aliasRowsFrom(stored)).toEqual([georgian]);
    expect(aliasRowsFrom(undefined)).toEqual([]);
  });

  it("offers the languages the item is not written in, and any that already has a name", () => {
    expect(aliasLanguages(["en", "ka", "ru"], ["en"])).toEqual(["ka", "ru"]);
    expect(aliasLanguages(["en", "ka", "ru"], [])).toEqual(["en", "ka", "ru"]);
    expect(aliasLanguages(["en", "ka", "ru"], ["en", "ka"], [georgian])).toEqual(["ka", "ru"]);
  });

  it("keeps only names in languages the business still uses", () => {
    expect(aliasesInLanguages([georgian, russian, hebrew], ["en", "ka", "he"])).toEqual([georgian, hebrew]);
  });

  it("adds the owner's name approved, with its spaces tidied", () => {
    const result = addAlias([georgian], "ru", "  Хачапури   с сыром ");
    expect(result).toEqual({
      ok: true,
      rows: [georgian, { language: "ru", text: "Хачапури с сыром", status: "approved" }],
    });
  });

  it("refuses an empty name, a long one, the same name twice and a fourth in a language", () => {
    expect(addAlias([], "ka", "   ")).toEqual({ ok: false, error: "validation.required" });
    expect(addAlias([], "ka", "ა".repeat(MAX_ALIAS_LENGTH + 1))).toEqual({
      ok: false,
      error: "knowledge.aliases.tooLong",
    });
    expect(addAlias([russian], "ru", "ХАЧАПУРИ  ПО-ИМЕРЕТИНСКИ")).toEqual({
      ok: false,
      error: "knowledge.aliases.duplicate",
    });
    // The same words in another language are another name.
    expect(addAlias([russian], "ka", "Хачапури по-имеретински").ok).toBe(true);
    const three: AliasRow[] = ["ერთი", "ორი", "სამი"].map((text) => ({ language: "ka", text, status: "approved" }));
    expect(addAlias(three, "ka", "ოთხი")).toEqual({ ok: false, error: "knowledge.aliases.tooMany" });
    expect(addAlias(three, "ru", "четыре").ok).toBe(true);
  });

  it("accepts a suggestion and removes a name by its place", () => {
    expect(acceptAlias([georgian, russian], 1)).toEqual([georgian, { ...russian, status: "approved" }]);
    expect(removeAlias([georgian, russian, hebrew], 1)).toEqual([georgian, hebrew]);
  });

  it("joins stored suggestions only in languages the form has no name in", () => {
    const stored: AliasRow[] = [georgian, { language: "ka", text: "ხაჭაპური", status: "suggested" }, russian, hebrew];
    const form: AliasRow[] = [{ language: "ka", text: "ჩემი", status: "approved" }];
    expect(mergeSuggestions(form, stored)).toEqual([...form, russian]);
    expect(countSuggested(mergeSuggestions(form, stored))).toBe(1);
  });

  it("compares two lists name by name, in order", () => {
    expect(sameAliases([georgian, russian], [georgian, russian])).toBe(true);
    expect(sameAliases([georgian, russian], [russian, georgian])).toBe(false);
    expect(sameAliases([georgian], [georgian, russian])).toBe(false);
    expect(sameAliases([russian], [{ ...russian, status: "approved" }])).toBe(false);
  });
});

describe("the knowledge form with names in other languages", () => {
  const item = {
    kind: "faq" as const,
    title: "Do you have parking?",
    body: "Yes, in the yard.",
    price_minor: null,
    duration_minutes: null,
    languages: ["en"],
    aliases: [georgian, russian],
  };

  it("opens with the stored names and creates an item with the typed ones", () => {
    const form = knowledgeFormFromItem(item, "GEL");
    expect(form.aliases).toEqual([georgian, russian]);
    expect(knowledgeFormFromItem({ ...item, aliases: undefined }, "GEL").aliases).toEqual([]);

    const created = { ...emptyKnowledgeForm("faq"), title: "Parking?", body: "Yes", aliases: [hebrew] };
    expect(knowledgeCreateBody(created, "GEL").aliases).toEqual([hebrew]);
  });

  it("sends the names only when they changed", () => {
    const initial = knowledgeFormFromItem(item, "GEL");
    expect(knowledgePatchBody({ ...initial }, initial, "GEL").aliases).toBeUndefined();

    const accepted = { ...initial, aliases: acceptAlias(initial.aliases, 1) };
    expect(knowledgePatchBody(accepted, initial, "GEL").aliases).toEqual([
      georgian,
      { ...russian, status: "approved" },
    ]);
  });
});

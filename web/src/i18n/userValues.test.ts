import { describe, expect, it } from "vitest";

import { en } from "./messages/en";
import { pseudoMessages } from "./pseudo";
import { createTranslator, interpolate } from "./translate";
import { interfaceSentence, joinSentences, splitUserValues, type SentencePart } from "./userValues";

/** The sentence as `t` would have written it with the values filled in. */
function joined(parts: SentencePart[]): string {
  return parts.map((part) => (part.kind === "text" ? part.text : part.value)).join("");
}

describe("splitUserValues", () => {
  it("cuts the sentence around each user value, in the language's own word order", () => {
    expect(splitUserValues("Handled by {name}", { name: "Тамар" })).toEqual([
      { kind: "text", text: "Handled by " },
      { kind: "value", name: "name", value: "Тамар" },
    ]);
    expect(splitUserValues("{customer} booked {resource} today", { customer: "Анна", resource: "Стол у окна" })).toEqual([
      { kind: "value", name: "customer", value: "Анна" },
      { kind: "text", text: " booked " },
      { kind: "value", name: "resource", value: "Стол у окна" },
      { kind: "text", text: " today" },
    ]);
  });

  it("keeps placeholders it has no value for, and a sentence without any as one text", () => {
    expect(splitUserValues("{count} new for {name}", { name: "Нино" })).toEqual([
      { kind: "text", text: "{count} new for " },
      { kind: "value", name: "name", value: "Нино" },
    ]);
    expect(splitUserValues("Nothing to name", { name: "Нино" })).toEqual([{ kind: "text", text: "Nothing to name" }]);
    expect(splitUserValues("", {})).toEqual([]);
    expect(splitUserValues("{toString}", {})).toEqual([{ kind: "text", text: "{toString}" }]);
  });

  it("drops the template's full stop after a value that ends with one, as interpolate does", () => {
    const template = "Closed: {note}. Back {when}.";
    for (const note of ["Санитарный день", "Санитарный день."]) {
      const values = { note, when: "tomorrow" };
      expect(joined(splitUserValues(template, values))).toBe(interpolate(template, values));
    }
  });

  it("joins sentences whose placeholders share a name without mixing their words", () => {
    const joinedSentence = joinSentences(
      [
        { text: "“{name}”", values: { name: "Лобио" } },
        interfaceSentence("opening hours"),
        { text: "“{name}”, {price}", values: { name: "Пхали" } },
      ],
      ", ",
    );
    expect(joinedSentence).toEqual({
      text: "“{name_1}”, opening hours, “{name_3}”, {price}",
      values: { name_1: "Лобио", name_3: "Пхали" },
    });
    expect(joined(splitUserValues(joinedSentence.text, joinedSentence.values))).toBe("“Лобио”, opening hours, “Пхали”, {price}");
    expect(joinSentences([], ", ")).toEqual({ text: "", values: {} });
  });

  it("reads a translation whose user placeholder `t` left in place, pseudo-locale included", () => {
    for (const messages of [en, pseudoMessages(en)]) {
      const { t } = createTranslator("en", messages, en);
      const parts = splitUserValues(t("shell.signedInAs"), { name: "Тамар" });
      expect(parts.filter((part) => part.kind === "value")).toEqual([{ kind: "value", name: "name", value: "Тамар" }]);
      expect(joined(parts)).toBe(t("shell.signedInAs", { name: "Тамар" }));
    }
  });
});

import { describe, expect, it } from "vitest";

import {
  draftBody,
  fieldCaption,
  fieldGroups,
  isDirty,
  problemMessage,
  shownText,
  startingValues,
  textProblem,
  type NicheTextEditor,
  type NicheTextField,
} from "./nicheTexts";

function field(fieldKey: string, overrides: Partial<NicheTextField> = {}): NicheTextField {
  return {
    field_key: fieldKey,
    section: fieldKey.startsWith("questions.") ? "question" : fieldKey.startsWith("starters.") ? "starters" : "niche",
    question_key: fieldKey.startsWith("questions.") ? fieldKey.split(".")[1] : null,
    code_text: `code ${fieldKey}`,
    english_text: `english ${fieldKey}`,
    max_length: 40,
    ...overrides,
  };
}

function editor(fields: NicheTextField[], hasDraft = false): NicheTextEditor {
  return {
    niche_key: "restaurant",
    language: "ru",
    languages: ["ka", "ru", "en", "he", "de"],
    status: {
      niche_key: "restaurant",
      name: "Рестораны",
      published_version: 1,
      override_count: 1,
      has_draft: hasDraft,
      draft_override_count: hasDraft ? 1 : 0,
    },
    fields,
    questions: [],
  };
}

describe("niche template editor", () => {
  it("starts from the draft while one waits, else from the published wording", () => {
    const fields = [field("name", { published_text: "Опубликовано", draft_text: "Черновик" }), field("description")];

    expect(startingValues(editor(fields))).toEqual({ name: "Опубликовано", description: "" });
    expect(startingValues(editor(fields, true))).toEqual({ name: "Черновик", description: "" });
  });

  it("notices a change, not spaces around the same words", () => {
    const start = { name: "Кафе", description: "" };

    expect(isDirty({ name: " Кафе ", description: "" }, start)).toBe(false);
    expect(isDirty({ name: "Бар", description: "" }, start)).toBe(true);
  });

  it("checks what the API checks", () => {
    const greeting = field("starters.faq.hello.answer", { code_text: "Привет, {name}!", max_length: 20 });

    expect(textProblem(greeting, "")).toBeNull();
    expect(textProblem(greeting, "Добрый день, {name}")).toBeNull();
    expect(textProblem(greeting, "Здравствуйте")).toEqual({ kind: "placeholders", names: "{name}" });
    expect(textProblem(greeting, "<b>{name}</b>")).toEqual({ kind: "html" });
    expect(textProblem(greeting, "две\nстроки {name}")).toEqual({ kind: "lineBreak" });
    expect(textProblem(greeting, "Очень длинное приветствие, {name}")).toEqual({ kind: "tooLong", max: 20 });
    expect(textProblem(field("name"), "Группы > 20, дети < 3")).toBeNull();
    expect(problemMessage({ kind: "tooLong", max: 20 })).toEqual(["adminNiches.editor.errors.tooLong", { max: 20 }]);
  });

  it("sends the language's own wording only", () => {
    const fields = [field("name"), field("description")];

    expect(draftBody(editor(fields), { name: "  Кафе ", description: "  " })).toEqual({
      language: "ru",
      texts: [{ field_key: "name", text: "Кафе" }],
    });
  });

  it("previews the wording, else the code's text in the language, else English", () => {
    expect(shownText(field("name"), { name: "Кафе" })).toBe("Кафе");
    expect(shownText(field("name"), { name: "" })).toBe("code name");
    expect(shownText(field("name", { code_text: null }), {})).toBe("english name");
    expect(shownText(undefined, {})).toBe("");
  });

  it("groups the fields by part and question", () => {
    const groups = fieldGroups(
      editor([
        field("starters.tone"),
        field("name"),
        field("questions.cuisine.label"),
        field("questions.cuisine.hint"),
        field("questions.delivery.label"),
      ]),
    );

    expect(groups.map((group) => [group.section, group.questionKey, group.fields.length])).toEqual([
      ["niche", null, 1],
      ["question", "cuisine", 2],
      ["question", "delivery", 1],
      ["starters", null, 1],
    ]);
  });

  it("names each kind of text", () => {
    expect(fieldCaption("questions.banquets.choices.separate_hall")).toEqual([
      "adminNiches.editor.fields.choice",
      { choice: "separate hall" },
    ]);
    expect(fieldCaption("handoff_rules.2")).toEqual(["adminNiches.editor.fields.handoffRule", { position: "2" }]);
    expect(fieldCaption("starters.faq.parking.answer")).toEqual(["adminNiches.editor.fields.faqAnswer", { entry: "parking" }]);
    expect(fieldCaption("starters.offers.business_lunch.title")[0]).toBe("adminNiches.editor.fields.offerTitle");
    expect(fieldCaption("starters.tone")).toEqual(["adminNiches.editor.fields.tone", {}]);
    expect(fieldCaption("questions.cuisine.hint")[0]).toBe("adminNiches.editor.fields.hint");
    expect(fieldCaption("something.else")).toEqual(["adminNiches.editor.fields.unknown", { key: "something.else" }]);
  });
});

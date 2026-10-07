import { describe, expect, it } from "vitest";

import type { QuickReplyView } from "@/lib/quickReplies";

import { bodyOf, cleanShortcut, draftErrors, draftOf, editorLanguages } from "./quickReplies";

const stored = {
  id: "quick_reply_1",
  title: "Table is ready",
  shortcut: "ready",
  variants: [
    { language: "ka", text: "{name}, მაგიდა მზადაა." },
    { language: "de", text: "{name}, Ihr Tisch ist bereit." },
  ],
  variables: ["name"],
} as unknown as QuickReplyView;

describe("the editor's languages", () => {
  it("are the business's, its default first, and any the reply still has", () => {
    expect(editorLanguages(["en", "ka", "ru"], "ka", null)).toEqual(["ka", "en", "ru"]);
    expect(editorLanguages(["en", "ka"], "ka", stored)).toEqual(["ka", "en", "de"]);
  });
});

describe("a draft", () => {
  const languages = ["ka", "en", "de"];

  it("starts empty for a new reply and holds the texts of a stored one", () => {
    expect(draftOf(null, languages)).toEqual({ title: "", shortcut: "", texts: { ka: "", en: "", de: "" } });
    expect(draftOf(stored, languages)).toEqual({
      title: "Table is ready",
      shortcut: "ready",
      texts: { ka: "{name}, მაგიდა მზადაა.", en: "", de: "{name}, Ihr Tisch ist bereit." },
    });
  });

  it("takes a shortcut without the slash and spaces", () => {
    expect(cleanShortcut("/table ready")).toBe("tableready");
    expect(cleanShortcut("//hours")).toBe("hours");
  });

  it("needs a name, a valid shortcut and one text at least", () => {
    expect(draftErrors({ title: " ", shortcut: "a b", texts: { ka: " ", en: "" } })).toEqual(["title", "shortcut", "texts"]);
    expect(draftErrors({ title: "Hours", shortcut: "hours", texts: { ka: "", en: "From noon" } })).toEqual([]);
    expect(draftErrors({ title: "Hours", shortcut: "hours", texts: { en: "x".repeat(2001) } })).toEqual(["tooLong"]);
  });

  it("becomes a body with the languages that have a text, in the editor's order", () => {
    const draft = { title: " Table is ready ", shortcut: "ready", texts: { ka: " მზადაა ", en: "", de: "Bereit" } };
    expect(bodyOf(draft, languages)).toEqual({
      title: "Table is ready",
      shortcut: "ready",
      variants: [
        { language: "ka", text: "მზადაა" },
        { language: "de", text: "Bereit" },
      ],
    });
  });
});

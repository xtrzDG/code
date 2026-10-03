import { describe, expect, it } from "vitest";

import { en } from "./messages/en";
import { PSEUDO_EXPANSION, pseudoLocalize, pseudoMessages, wantsPseudoLocale } from "./pseudo";
import { createTranslator, lookupMessage } from "./translate";

describe("pseudo-locale", () => {
  it("accents every Latin letter, keeps placeholders and adds 40 % in brackets", () => {
    const text = pseudoLocalize("Signed in as {name}");

    expect(text.startsWith("[Šíĝñéð íñ áš {name} ")).toBe(true);
    expect(text.endsWith("]")).toBe(true);
    const visible = "Signed in as ".length;
    expect(text.length).toBeGreaterThanOrEqual("[Signed in as {name}]".length + Math.ceil(visible * PSEUDO_EXPANSION));
    expect(pseudoLocalize("")).toBe("[]");
  });

  it("maps all 52 Latin letters to one accented character each", () => {
    const letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
    const accented = pseudoLocalize(letters).slice(1, letters.length + 1);
    expect([...accented]).toHaveLength(letters.length);
    expect(/[a-zA-Z]/.test(accented)).toBe(false);
  });

  it("breaks long padding into words that can wrap", () => {
    const words = pseudoLocalize("A text long enough to need more than one filler word here").slice(0, -1).split(" ");
    expect(Math.max(...words.map((word) => word.length))).toBeLessThanOrEqual(12);
  });

  it("turns a whole dictionary, plural forms and interpolation included", () => {
    const pseudo = pseudoMessages(en);
    const { t, tp } = createTranslator("en", pseudo, en);

    expect(lookupMessage(pseudo, "common.save")).toMatch(/^\[Šáṽé ẋ+\]$/);
    expect(t("shell.signedInAs", { name: "Nino" })).toContain("Nino");
    expect(tp("navigation.waiting", 3)).toMatch(/^\[3 /);
  });

  it("is served only when the server allows it and the cookie asks for it", () => {
    expect(wantsPseudoLocale("en-XA", { PSEUDO_LOCALE: "true" })).toBe(true);
    expect(wantsPseudoLocale("en_xa", { PSEUDO_LOCALE: "true" })).toBe(true);
    expect(wantsPseudoLocale("en-XA", {})).toBe(false);
    expect(wantsPseudoLocale("en", { PSEUDO_LOCALE: "true" })).toBe(false);
    expect(wantsPseudoLocale(undefined, { PSEUDO_LOCALE: "true" })).toBe(false);
  });
});

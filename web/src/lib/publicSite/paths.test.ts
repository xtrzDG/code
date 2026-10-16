import { describe, expect, it } from "vitest";

import {
  LEGAL_PAGES,
  isLegalPage,
  languageAlternates,
  legalPath,
  localeHomePath,
  localizedRedirectPath,
  nichePath,
  pathLocale,
  switchPathLocale,
} from "./paths";

describe("public site paths", () => {
  it("puts every public page under its language", () => {
    expect(localeHomePath("ka")).toBe("/ka");
    expect(nichePath("ru", "beauty_salon")).toBe("/ru/for/beauty_salon");
    expect(nichePath("en", "a b")).toBe("/en/for/a%20b");
    expect(legalPath("en", "privacy")).toBe("/en/privacy");
    expect(LEGAL_PAGES).toContain("contact");
    expect(isLegalPage("dpa")).toBe(true);
    expect(isLegalPage("refunds")).toBe(false);
  });

  it("reads the language of a path and swaps it", () => {
    expect(pathLocale("/ru/for/hotel")).toBe("ru");
    expect(pathLocale("/ka")).toBe("ka");
    expect(pathLocale("/login")).toBeNull();
    expect(pathLocale("/")).toBeNull();
    expect(switchPathLocale("/ru/for/hotel", "ka")).toBe("/ka/for/hotel");
    expect(switchPathLocale("/en", "ru")).toBe("/ru");
    expect(switchPathLocale("/businesses", "ru")).toBe("/businesses");
  });

  it("sends a legal page without a language to the reader's", () => {
    expect(localizedRedirectPath("/privacy", "ru")).toBe("/ru/privacy");
    expect(localizedRedirectPath("/terms/", "ka")).toBe("/ka/terms");
    expect(localizedRedirectPath("/login", "en")).toBeNull();
    expect(localizedRedirectPath("/", "en")).toBeNull();
  });

  it("links every language of a page with an x-default", () => {
    expect(languageAlternates("")).toEqual({ ka: "/ka", ru: "/ru", en: "/en", he: "/he", de: "/de", "x-default": "/" });
    expect(languageAlternates("/for/hotel")).toEqual({
      ka: "/ka/for/hotel",
      ru: "/ru/for/hotel",
      en: "/en/for/hotel",
      he: "/he/for/hotel",
      de: "/de/for/hotel",
      "x-default": "/en/for/hotel",
    });
  });
});

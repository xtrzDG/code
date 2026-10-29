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
    expect(localeHomePath("it")).toBe("/it");
    expect(nichePath("it", "beauty_salon")).toBe("/it/for/beauty_salon");
    expect(nichePath("en", "a b")).toBe("/en/for/a%20b");
    expect(legalPath("en", "privacy")).toBe("/en/privacy");
    expect(LEGAL_PAGES).toContain("contact");
    expect(isLegalPage("dpa")).toBe(true);
    expect(isLegalPage("refunds")).toBe(false);
  });

  it("reads the language of a path and swaps it", () => {
    expect(pathLocale("/it/for/hotel")).toBe("it");
    expect(pathLocale("/en")).toBe("en");
    expect(pathLocale("/login")).toBeNull();
    expect(pathLocale("/")).toBeNull();
    // A language the site no longer has is not a public path.
    expect(pathLocale("/ru/for/hotel")).toBeNull();
    expect(switchPathLocale("/it/for/hotel", "en")).toBe("/en/for/hotel");
    expect(switchPathLocale("/en", "it")).toBe("/it");
    expect(switchPathLocale("/businesses", "it")).toBe("/businesses");
  });

  it("sends a legal page without a language to the reader's", () => {
    expect(localizedRedirectPath("/privacy", "it")).toBe("/it/privacy");
    expect(localizedRedirectPath("/terms/", "it")).toBe("/it/terms");
    expect(localizedRedirectPath("/login", "en")).toBeNull();
    expect(localizedRedirectPath("/", "en")).toBeNull();
  });

  it("links every language of a page with an x-default", () => {
    expect(languageAlternates("")).toEqual({ en: "/en", it: "/it", "x-default": "/" });
    expect(languageAlternates("/for/hotel")).toEqual({
      en: "/en/for/hotel",
      it: "/it/for/hotel",
      "x-default": "/en/for/hotel",
    });
  });
});

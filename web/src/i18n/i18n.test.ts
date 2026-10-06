import { describe, expect, it } from "vitest";

import { CABINET_LANGUAGES, LOCALES, matchLocale, negotiateLocale, resolveLocale } from "./config";
import { DICTIONARIES, getMessages } from "./messages";
import { en } from "./messages/en";
import { createTranslator, interpolate, lookupMessage, mergeMessages, type MessageTree } from "./translate";

function leafKeys(tree: MessageTree, prefix = ""): string[] {
  return Object.entries(tree).flatMap(([key, value]) =>
    typeof value === "string" ? [`${prefix}${key}`] : value ? leafKeys(value, `${prefix}${key}.`) : [],
  );
}

describe("locale negotiation", () => {
  it("matches tags to the supported languages", () => {
    expect(matchLocale("ru-RU")).toBe("ru");
    expect(matchLocale("ka")).toBe("ka");
    expect(matchLocale("EN_us")).toBe("en");
    expect(matchLocale("de-DE")).toBeNull();
    expect(matchLocale(undefined)).toBeNull();
  });

  it("honours Accept-Language quality values", () => {
    expect(negotiateLocale("de-DE,ru;q=0.8,en;q=0.5")).toBe("ru");
    expect(negotiateLocale("en;q=0.4, ka;q=0.9")).toBe("ka");
    expect(negotiateLocale("fr, de")).toBeNull();
    expect(negotiateLocale("*")).toBeNull();
  });

  it("prefers the cookie, then the browser, then English", () => {
    expect(resolveLocale({ cookieValue: "ka", acceptLanguage: "ru" })).toBe("ka");
    expect(resolveLocale({ cookieValue: "xx", acceptLanguage: "ru-RU" })).toBe("ru");
    expect(resolveLocale({})).toBe("en");
  });
});

describe("translator", () => {
  const partialGeorgian: MessageTree = { common: { save: "შენახვა" } };

  it("falls back to English for a missing text, then to the key", () => {
    const { t, has } = createTranslator("ka", partialGeorgian, en);
    expect(t("common.save")).toBe("შენახვა");
    expect(t("common.cancel")).toBe(en.common.cancel);
    expect(has("common.cancel")).toBe(true);
    expect(has("no.such.key")).toBe(false);
  });

  it("returns the key itself when no dictionary has the text", () => {
    const { tDynamic } = createTranslator("ka", partialGeorgian);
    expect(tDynamic("errors.codes.unknown", "fallback")).toBe("fallback");
  });

  it("merges a partial dictionary over English", () => {
    const merged = mergeMessages(en, partialGeorgian);
    expect(lookupMessage(merged, "common.save")).toBe("შენახვა");
    expect(lookupMessage(merged, "common.cancel")).toBe(en.common.cancel);
  });

  it("interpolates placeholders and keeps unknown ones", () => {
    expect(interpolate("Step {number} of {total}", { number: 2, total: 6 })).toBe("Step 2 of 6");
    expect(interpolate("Hi {name}", {})).toBe("Hi {name}");
    expect(interpolate("Hi {name}.", {})).toBe("Hi {name}.");
  });

  it("does not double the full stop after a value that ends with one", () => {
    expect(interpolate("До {date}. Оплатите", { date: "4 окт. 2026 г." })).toBe("До 4 окт. 2026 г. Оплатите");
    expect(interpolate("Until {date}. Pay", { date: "Oct 4, 2026" })).toBe("Until Oct 4, 2026. Pay");
    expect(interpolate("{a}.{b}", { a: "x.", b: "y" })).toBe("x.y");
  });

  it("picks plural forms by language rules", () => {
    const { tp } = createTranslator("ru", getMessages("ru"), en);
    expect(tp("onboarding.gaps.times", 1)).toBe("1 раз");
    expect(tp("onboarding.gaps.times", 3)).toBe("3 раза");
    expect(tp("onboarding.gaps.times", 5)).toBe("5 раз");
    const english = createTranslator("en", en);
    expect(english.tp("onboarding.gaps.times", 1)).toBe("1 time");
    expect(english.tp("onboarding.gaps.times", 2)).toBe("2 times");
  });
});

/** The English texts every dictionary needs (plural forms other than `other` are the language's own). */
const REFERENCE_KEYS = leafKeys(en).filter((key) => !/\.(zero|one|two|few|many)$/.test(key));

function missingKeys(locale: (typeof LOCALES)[number]): string[] {
  const keys = new Set(leafKeys(DICTIONARIES[locale]));
  return REFERENCE_KEYS.filter((key) => !keys.has(key));
}

describe("dictionaries", () => {
  it("are complete in every language owners can choose", () => {
    for (const locale of CABINET_LANGUAGES) {
      expect(missingKeys(locale), locale).toEqual([]);
    }
  });

  it("offer every complete language, and only complete ones (a draft stays out of the picker)", () => {
    for (const locale of LOCALES) {
      const complete = missingKeys(locale).length === 0;
      expect(CABINET_LANGUAGES.includes(locale), `${locale}: ${complete ? "complete" : "incomplete"}`).toBe(complete);
    }
  });

  it("never end a sentence on a formatted date (a Russian one ends with “г.”)", () => {
    const endsOnDate = /\{(date|when|until|time|start|end|from|to|day)\}\./;
    for (const locale of LOCALES) {
      const offending = leafKeys(DICTIONARIES[locale]).filter((key) => {
        const text = lookupMessage(DICTIONARIES[locale], key);
        return typeof text === "string" && endsOnDate.test(text);
      });
      expect(offending, locale).toEqual([]);
    }
  });

  it("keep the placeholders of the English texts", () => {
    const placeholders = (text: string) => [...new Set([...text.matchAll(/\{(\w+)\}/g)].map((match) => match[1]))].sort();
    for (const locale of LOCALES.filter((code) => code !== "en")) {
      for (const key of leafKeys(DICTIONARIES[locale])) {
        const translated = lookupMessage(DICTIONARIES[locale], key);
        const plural = /\.(zero|one|two|few|many|other)$/.test(key);
        // A plural form may say "a minute" for {count} = 1: its placeholders are among the English text's.
        const original = lookupMessage(en, plural ? key.replace(/\.\w+$/, ".other") : key);
        if (typeof translated !== "string" || typeof original !== "string") {
          continue;
        }
        if (plural) {
          expect(placeholders(original), `${locale}:${key}`).toEqual(expect.arrayContaining(placeholders(translated)));
        } else {
          expect(placeholders(translated), `${locale}:${key}`).toEqual(placeholders(original));
        }
      }
    }
  });

  it("have no text the English dictionary does not have", () => {
    const reference = new Set(leafKeys(en).map((key) => key.replace(/\.(zero|one|two|few|many|other)$/, "")));
    for (const locale of LOCALES) {
      const extra = leafKeys(DICTIONARIES[locale]).filter((key) => !reference.has(key.replace(/\.(zero|one|two|few|many|other)$/, "")));
      expect(extra, locale).toEqual([]);
    }
  });
});

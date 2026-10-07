import { describe, expect, it } from "vitest";

import { LOCALES } from "./config";
import { DICTIONARIES } from "./messages";
import { en } from "./messages/en";
import { createTranslator, type MessageTree } from "./translate";

/** Placeholders that hold a number of things. */
const COUNTS =
  "count|total|done|days|minutes|hours|max|size|scanned|estimate|batches|passed|played|included|used|cap|window|" +
  "then|eligible|ended|failures|rate|limit|open|booked|requests|bookings|replies|calls|bad|unanswered";

/** "{count} webhooks", "{done} of {total} steps", "{scanned} of about {estimate} rows": a count before a plural noun. */
const COUNT_BEFORE_PLURAL = new RegExp(`\\{(?:${COUNTS})\\}(?: of(?: about)? \\{\\w+\\})? (?:[a-z]+ )?[a-z]{3,}s\\b`);

/**
 * Texts that keep one form: the landing page's own (its counts are never
 * one: a 14-day trial, 16 kinds of business, dozens of countries) and the
 * plan cards it shares with Billing (hundreds of minutes and dialogs).
 */
const ALWAYS_MANY = new Set([
  "landing.hero.trial",
  "landing.niches.subtitle",
  "landing.world.phoneText",
  "billing.plans.voiceMinutes",
  "billing.plans.dialogs",
]);

const PLURAL_CATEGORIES = new Set(["zero", "one", "two", "few", "many", "other"]);

/** Plural forms are an object of plural categories only (a section may have its own `other` text). */
const isPluralForms = (value: MessageTree): boolean => Object.keys(value).every((key) => PLURAL_CATEGORIES.has(key));

function plainTexts(tree: MessageTree, prefix = ""): [string, string][] {
  return Object.entries(tree).flatMap(([key, value]): [string, string][] => {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === "string") {
      return [[path, value]];
    }
    if (!value || isPluralForms(value)) {
      return [];
    }
    return plainTexts(value, path);
  });
}

describe("counted texts", () => {
  it("give a count before a noun its plural forms (no “1 calls answered”)", () => {
    const offending = plainTexts(en as unknown as MessageTree)
      .filter(([key, text]) => COUNT_BEFORE_PLURAL.test(text) && !ALWAYS_MANY.has(key))
      .map(([key, text]) => `${key}: ${text}`);
    expect(offending).toEqual([]);
  });

  it.each(LOCALES)("read right for one and for many in %s", (locale) => {
    const { tp, t } = createTranslator(locale, DICTIONARIES[locale], en as unknown as MessageTree);
    const one = tp("value.hero.savedCalls", 1, { count: "1" });
    const many = tp("value.hero.savedCalls", 5, { count: "5" });
    expect(one).not.toBe(many);
    expect(t("value.hero.savedHint", { replies: "{r}", calls: "{c}" })).toMatch(/\{r\}.*\{c\}/);
  });

  it("say “1 call answered” and “3 calls answered” in English", () => {
    const { t, tp } = createTranslator("en", en as unknown as MessageTree);
    const hint = (replies: number, calls: number) =>
      t("value.hero.savedHint", {
        replies: tp("value.hero.savedReplies", replies),
        calls: tp("value.hero.savedCalls", calls),
      });
    expect(hint(1, 1)).toBe("1 reply written and 1 call answered for you");
    expect(hint(12, 3)).toBe("12 replies written and 3 calls answered for you");
  });

  it("follow Russian agreement after a number", () => {
    const { tp } = createTranslator("ru", DICTIONARIES.ru, en as unknown as MessageTree);
    expect([1, 3, 5, 21].map((count) => tp("value.hero.savedCalls", count))).toEqual([
      "принят 1 звонок",
      "принято 3 звонка",
      "принято 5 звонков",
      "принят 21 звонок",
    ]);
    expect([1, 2, 5].map((total) => tp("setup.progress", total, { done: 1, total }))).toEqual([
      "Готово 1 из 1 шага",
      "Готово 1 из 2 шагов",
      "Готово 1 из 5 шагов",
    ]);
  });
});

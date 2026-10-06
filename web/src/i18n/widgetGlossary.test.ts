/**
 * The words of the website chat (widget.js and the hosted chat page that
 * runs it), checked on the widget's own text bundles
 * (app/gateways/http/static/widget/texts_*.js) like the cabinet's
 * dictionaries in glossary.test.ts:
 *
 * - every language is written in its own script ("AI" and the brand aside);
 * - customers meet an "AI-ассистент" (docs/glossary.md, "Words customers
 *   read"): the header, the greeting and the footer say it, the way the AI
 *   disclosure does; "помощник" is the cabinet's word, "бот" nobody's.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { runInNewContext } from "node:vm";

import { describe, expect, it } from "vitest";

const WIDGET_DIRECTORY = fileURLToPath(
  new URL("../../../app/gateways/http/static/widget/", import.meta.url),
);
// The order widget_script_assembly.py joins them in: one `var TEXTS = {…};`.
const TEXT_PARTS = [
  "texts_latin_west.js",
  "texts_latin_north_baltic.js",
  "texts_cyrillic_caucasus_turkic.js",
  "texts_middle_east_asia.js",
];

type WidgetTexts = Record<string, Record<string, string>>;

function loadWidgetTexts(): WidgetTexts {
  const source = TEXT_PARTS.map((part) =>
    readFileSync(`${WIDGET_DIRECTORY}${part}`, "utf8"),
  ).join("");
  const sandbox: { TEXTS?: WidgetTexts } = {};
  runInNewContext(source, sandbox);
  if (!sandbox.TEXTS) {
    throw new Error("the widget's text bundles define no TEXTS");
  }
  return sandbox.TEXTS;
}

const TEXTS = loadWidgetTexts();

const LATIN = /\p{scx=Latin}/u;
/** The script of each interface language's letters. */
const SCRIPTS: Record<string, RegExp> = {
  ru: /\p{scx=Cyrillic}/u,
  uk: /\p{scx=Cyrillic}/u,
  kk: /\p{scx=Cyrillic}/u,
  ka: /\p{scx=Georgian}/u,
  hy: /\p{scx=Armenian}/u,
  he: /\p{scx=Hebrew}/u,
  ar: /\p{scx=Arabic}/u,
  fa: /\p{scx=Arabic}/u,
  ur: /\p{scx=Arabic}/u,
  hi: /\p{scx=Devanagari}/u,
  zh: /\p{scx=Han}/u,
  ja: /\p{scx=Hiragana}|\p{scx=Katakana}|\p{scx=Han}/u,
  ko: /\p{scx=Hangul}/u,
};

/** Latin words every language keeps: "AI" and the platform's name. */
const KEPT_LATIN = /\bAI\b|Assistant Workshop/g;

/** The letters of a text outside its language's script (placeholders and kept names aside). */
function foreignLetters(language: string, text: string): string {
  const own = SCRIPTS[language] ?? LATIN;
  const letters =
    text
      .replace(/\{[^}]*\}/g, " ")
      .replace(KEPT_LATIN, " ")
      .match(/\p{L}/gu) ?? [];
  return letters.filter((letter) => !own.test(letter)).join("");
}

describe("the website chat's texts", () => {
  it("have every language the script table names", () => {
    const missing = Object.keys(SCRIPTS).filter(
      (language) => !(language in TEXTS),
    );
    expect(missing).toEqual([]);
    expect(Object.keys(TEXTS).length).toBeGreaterThanOrEqual(29);
  });

  it("are each in their own language's script", () => {
    const wrong = Object.entries(TEXTS).flatMap(([language, texts]) =>
      Object.entries(texts)
        .filter(([, text]) => foreignLetters(language, text) !== "")
        .map(([key, text]) => `${language}.${key}: ${text}`),
    );
    expect(wrong).toEqual([]);
  });
});

describe("the customer's glossary", () => {
  it("introduces an AI assistant in the header, the greeting and the footer", () => {
    const expected: Record<string, string> = {
      en: "AI assistant",
      ru: "AI-ассистент",
      ka: "AI-ასისტენტი",
    };
    for (const [language, name] of Object.entries(expected)) {
      const texts = TEXTS[language] ?? {};
      for (const key of ["subtitle", "greeting", "footer"]) {
        expect(texts[key], `${language}.${key}`).toContain(name);
      }
    }
  });

  it("never calls the assistant a helper or a bot in Russian", () => {
    const wrong = Object.entries(TEXTS.ru ?? {}).filter(([, text]) =>
      /помощник|(?<!\p{L})(чат-)?бот|(?<!\p{L})ИИ(?!\p{L})/iu.test(text),
    );
    expect(wrong).toEqual([]);
  });

  it("tells a visitor whose answer is late that the team will answer", () => {
    expect(TEXTS.ru?.noAnswer).toBe("Мы ответим, как только сможем.");
    expect(Object.values(TEXTS).every((texts) => Boolean(texts.noAnswer))).toBe(
      true,
    );
  });
});

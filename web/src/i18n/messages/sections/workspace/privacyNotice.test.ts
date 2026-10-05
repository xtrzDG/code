import { describe, expect, it } from "vitest";

import { privacyNoticeEn } from "./privacyNotice.en";
import { privacyNoticeKa } from "./privacyNotice.ka";
import { privacyNoticeRu } from "./privacyNotice.ru";

/** Headings and labels: short names, not sentences. */
const LABEL_KEYS = /(^title$|^subtitle$|Title$|^backToChat$)/;

/**
 * Words a sentence never ends on: possessives, articles, prepositions and
 * conjunctions ("…попросить удалить ваш." was cut off mid-sentence).
 */
const DANGLING_WORDS: Record<string, ReadonlySet<string>> = {
  en: new Set(["your", "the", "a", "an", "and", "or", "of", "to", "for", "with", "by", "in", "on", "at", "from"]),
  ru: new Set(["ваш", "ваша", "ваше", "ваши", "вашего", "и", "или", "в", "во", "на", "с", "со", "для", "по", "к", "о", "об", "от", "за", "из", "у", "а", "но"]),
  ka: new Set(["თქვენი", "და", "ან", "მისი", "ეს", "ის"]),
};

const NOTICES = { en: privacyNoticeEn, ru: privacyNoticeRu, ka: privacyNoticeKa } as const;

function sentences(notice: Record<string, string>): [string, string][] {
  return Object.entries(notice).filter(([key]) => !LABEL_KEYS.test(key));
}

describe("the hosted chat's privacy notice", () => {
  for (const [language, notice] of Object.entries(NOTICES)) {
    it(`ends every text with a full sentence in ${language}`, () => {
      const dangling = DANGLING_WORDS[language] ?? new Set<string>();
      for (const [key, text] of sentences(notice)) {
        expect(text.trim(), `${language}.${key}`).toMatch(/[.!?»)]$/);
        const lastWord = text.trim().replace(/[.!?»)]+$/, "").split(/\s+/).at(-1)?.toLocaleLowerCase(language) ?? "";
        expect(dangling.has(lastWord), `${language}.${key} ends on “${lastWord}”`).toBe(false);
      }
    });
  }

  it("has the same texts in every language", () => {
    expect(Object.keys(privacyNoticeRu).sort()).toEqual(Object.keys(privacyNoticeEn).sort());
    expect(Object.keys(privacyNoticeKa).sort()).toEqual(Object.keys(privacyNoticeEn).sort());
  });
});

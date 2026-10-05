import { describe, expect, it } from "vitest";

import { en } from "@/i18n/messages/en";
import { HOSTED_CHAT_LANGUAGES } from "@/lib/hostedChat/texts";

import { PRIVACY_NOTICE_DRAFTS, privacyNoticeFor } from "./privacyNoticeTexts";

const REVIEWED = ["en", "ru", "ka"];
const placeholders = (text: string) => new Set(text.match(/\{\w+\}/g) ?? []);

describe("privacy notice languages", () => {
  it("has a reviewed text or a draft for every language of the chat widget", () => {
    const missing = HOSTED_CHAT_LANGUAGES.filter(
      (language) => !REVIEWED.includes(language) && !(language in PRIVACY_NOTICE_DRAFTS),
    );
    expect(missing).toEqual([]);
  });

  it("marks every draft for review until a translator and a lawyer checked it", () => {
    for (const [language, draft] of Object.entries(PRIVACY_NOTICE_DRAFTS)) {
      expect([language, draft.status]).toEqual([language, "needs_review"]);
    }
  });

  it("gives every draft every text, using only the values the page passes", () => {
    const keys = Object.keys(en.privacyNotice).sort();
    for (const [language, draft] of Object.entries(PRIVACY_NOTICE_DRAFTS)) {
      const draftKeys = Object.keys(draft.texts).filter((key) => key !== "draftNote" && key !== "readInEnglish");
      expect([language, draftKeys.sort()]).toEqual([language, keys]);
      for (const key of keys) {
        const english = placeholders(en.privacyNotice[key as keyof typeof en.privacyNotice]);
        const translated = placeholders(draft.texts[key as keyof typeof draft.texts]);
        for (const name of translated) {
          expect([language, key, english.has(name)]).toEqual([language, key, true]);
        }
        if (english.has("{business}") && key !== "title") {
          expect([language, key, translated.has("{business}")]).toEqual([language, key, true]);
        }
      }
      expect(draft.texts.draftNote.length).toBeGreaterThan(10);
      expect(draft.texts.readInEnglish.length).toBeGreaterThan(2);
    }
  });
});

describe("privacyNoticeFor", () => {
  it("reads the reviewed cabinet texts in English, Russian and Georgian", () => {
    const russian = privacyNoticeFor("ru-RU");
    expect(russian.language).toBe("ru");
    expect(russian.needsReview).toBe(false);
    expect(russian.text("title")).toBe("Политика конфиденциальности");
    expect(privacyNoticeFor("ka").text("subtitle", { business: "ია" })).toContain("ია");
  });

  it("reads a draft, marked for review, in the other widget languages", () => {
    const german = privacyNoticeFor("de-AT");
    expect(german.language).toBe("de");
    expect(german.needsReview).toBe(true);
    expect(german.text("subtitle", { business: "Café Ia" })).toBe(
      "Wie Café Ia mit dem umgeht, was Sie in den Chat schreiben",
    );
    expect(privacyNoticeFor("ar").text("backToChat")).toBe("العودة إلى المحادثة");
  });

  it("falls back to English for a language with neither", () => {
    const swahili = privacyNoticeFor("sw");
    expect(swahili.language).toBe("en");
    expect(swahili.needsReview).toBe(false);
    expect(swahili.text("title")).toBe(en.privacyNotice.title);
  });
});

import { describe, expect, it } from "vitest";

import { en } from "@/i18n/messages/en";
import { HOSTED_CHAT_LANGUAGES } from "@/lib/hostedChat/texts";

import { PRIVACY_NOTICE_DRAFTS, privacyNoticeFor } from "./privacyNoticeTexts";

/** The cabinet languages whose notice a native reviewer read (CABINET_LANGUAGES minus NEEDS_REVIEW_LOCALES). */
const REVIEWED = ["en"];
const placeholders = (text: string) => new Set(text.match(/\{\w+\}/g) ?? []);

describe("privacy notice languages", () => {
  it("has a reviewed text or a draft for every language of the chat widget", () => {
    const missing = HOSTED_CHAT_LANGUAGES.filter(
      (language) => !REVIEWED.includes(language) && !(language in PRIVACY_NOTICE_DRAFTS),
    );
    expect(missing).toEqual([]);
  });

  it("marks every draft for review until a translator and a lawyer checked it", () => {
    // Russian and Georgian were the cabinet's reviewed texts before the cabinet spoke English and Italian only.
    const reviewedTexts = ["ru", "ka"];
    for (const [language, draft] of Object.entries(PRIVACY_NOTICE_DRAFTS)) {
      expect([language, draft.status]).toEqual([language, reviewedTexts.includes(language) ? "reviewed" : "needs_review"]);
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
  it("reads the reviewed cabinet texts in English, and Italian's draft while its cabinet texts await review", () => {
    const english = privacyNoticeFor("en-GB");
    expect(english.language).toBe("en");
    expect(english.needsReview).toBe(false);
    expect(english.text("title")).toBe(en.privacyNotice.title);
    expect(english.text("subtitle", { business: "Ia" })).toContain("Ia");
    const italian = privacyNoticeFor("it-IT");
    expect(italian.language).toBe("it");
    expect(italian.needsReview).toBe(true);
    expect(italian.text("title")).toBe(PRIVACY_NOTICE_DRAFTS.it?.texts.title);
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

  it("names how long call recordings are kept where the page knows the period", () => {
    expect(privacyNoticeFor("ru").text("callsKept", { recordings: "3 месяца" })).toContain("3 месяца");
    expect(privacyNoticeFor("de").text("callsKept", { recordings: "3 Monate" })).toContain("3 Monate");
    // A draft in a language the cabinet does not speak names no period, so it needs none.
    expect(privacyNoticeFor("fr").text("callsKept")).not.toContain("{recordings}");
  });

  it("tells callers apart from the notice where the law asks their consent", () => {
    for (const language of ["en", "ru", "ka", "he", "de", "fr", "ja"]) {
      const notice = privacyNoticeFor(language);
      expect([language, notice.text("callsConsent") === notice.text("callsNotice")]).toEqual([language, false]);
    }
  });

  it("describes the consent call as the greeting makes it: told, and free to refuse", () => {
    // The greeting says the call is recorded and that the caller may refuse;
    // it asks no yes-or-no question, so the notice must not claim one.
    const consent = privacyNoticeFor("en").text("callsConsent");
    expect(consent).toContain("is recorded");
    expect(consent).toContain("refuse");
    expect(consent).not.toMatch(/asks whether/);
    expect(privacyNoticeFor("ru").text("callsConsent")).not.toContain("спрашивает");
    expect(privacyNoticeFor("de").text("callsConsent")).not.toContain("fragt");
  });
});

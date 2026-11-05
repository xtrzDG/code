import { describe, expect, it } from "vitest";

import { BOOKING_DATE_TEXTS, bookingDateTexts } from "./dateTexts";
import { BOOKING_PAGE_LANGUAGES } from "./texts";

const ENGLISH = BOOKING_DATE_TEXTS.en!;

describe("booking page date field texts", () => {
  it("speak every language the page speaks", () => {
    expect(Object.keys(BOOKING_DATE_TEXTS).sort()).toEqual([...BOOKING_PAGE_LANGUAGES].sort());
  });

  it.each(Object.entries(BOOKING_DATE_TEXTS))("%s has every text, translated", (language, texts) => {
    expect(Object.keys(texts).sort()).toEqual(Object.keys(ENGLISH).sort());
    for (const [key, text] of Object.entries(texts)) {
      expect(text.trim(), `${language}.${key}`).not.toBe("");
    }
    if (language !== "en") {
      expect(texts.open, language).not.toBe(ENGLISH.open);
      expect(texts.pastDate, language).not.toBe(ENGLISH.pastDate);
    }
  });

  it("read regional tags and fall back to English", () => {
    expect(bookingDateTexts("pt-BR")).toBe(BOOKING_DATE_TEXTS.pt);
    expect(bookingDateTexts("he-IL").open).toBe("פתיחת לוח השנה");
    expect(bookingDateTexts("fa")).toBe(ENGLISH);
  });
});

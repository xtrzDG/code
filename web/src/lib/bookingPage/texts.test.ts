import { describe, expect, it } from "vitest";

import { BOOKING_PAGE_LANGUAGES, BOOKING_PAGE_TEXTS, bookingPageTexts, hasBookingPageTexts } from "./texts";

const ENGLISH = BOOKING_PAGE_TEXTS.en!;
const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((match) => match[1]).sort();

/** The languages of the written confirmation (app/utilities/bookings/booking_confirmation_texts.py). */
const CONFIRMATION_LANGUAGES = ["en", "ru", "ka", "uk", "hy", "he", "ar", "tr", "pl", "de", "es", "fr", "it", "pt", "kk"];

describe("booking page texts", () => {
  it("speak every language a confirmation is written in", () => {
    expect([...BOOKING_PAGE_LANGUAGES].sort()).toEqual([...CONFIRMATION_LANGUAGES].sort());
  });

  it.each(Object.entries(BOOKING_PAGE_TEXTS))("%s has every text, with the same placeholders", (language, texts) => {
    expect(Object.keys(texts).sort()).toEqual(Object.keys(ENGLISH).sort());
    for (const [key, text] of Object.entries(texts)) {
      expect(text.trim(), `${language}.${key}`).not.toBe("");
      expect(placeholders(text), `${language}.${key}`).toEqual(placeholders(ENGLISH[key as keyof typeof ENGLISH]));
    }
  });

  it("are real translations, not English copies", () => {
    for (const [language, texts] of Object.entries(BOOKING_PAGE_TEXTS)) {
      if (language !== "en") {
        expect(texts.cancel, language).not.toBe(ENGLISH.cancel);
        expect(texts.writeToUs, language).not.toBe(ENGLISH.writeToUs);
      }
    }
  });

  it("read regional tags and fall back to English", () => {
    expect(bookingPageTexts("ka-GE")).toBe(BOOKING_PAGE_TEXTS.ka);
    expect(bookingPageTexts("ru")).toMatchObject({ writeToUs: "Написать нам" });
    expect(bookingPageTexts("fa")).toBe(ENGLISH);
    expect(hasBookingPageTexts("he-IL")).toBe(true);
    expect(hasBookingPageTexts("fa")).toBe(false);
  });
});

import { describe, expect, it } from "vitest";

import { BOOKING_PAGE_LANGUAGES } from "@/lib/bookingPage/texts";

import { MARKETING_CONSENT_TEXTS, MARKETING_CONSENT_TEXT_VERSION, marketingConsentTexts } from "./consentTexts";

describe("the marketing box's texts", () => {
  it("speak every language of the booking page and name the business", () => {
    expect(Object.keys(MARKETING_CONSENT_TEXTS).sort()).toEqual([...BOOKING_PAGE_LANGUAGES].sort());
    for (const texts of Object.values(MARKETING_CONSENT_TEXTS)) {
      expect(texts.label).toContain("{business}");
      expect(texts.note.length).toBeGreaterThan(0);
      expect(texts.failed.length).toBeGreaterThan(0);
    }
  });

  it("fall back to English and carry the stored version of the wording", () => {
    expect(marketingConsentTexts("pt-BR")).toBe(MARKETING_CONSENT_TEXTS.pt);
    expect(marketingConsentTexts("xx")).toBe(MARKETING_CONSENT_TEXTS.en);
    expect(MARKETING_CONSENT_TEXT_VERSION).toBe("2026-11-02");
  });
});

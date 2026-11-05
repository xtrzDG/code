import { describe, expect, it } from "vitest";

import {
  currencyFractionDigits,
  decimalInputValue,
  formatDate,
  formatNumber,
  formatTime,
  languageName,
} from "./format";

// 2026-10-05 09:30 UTC in API microseconds.
const MONDAY_MORNING = Date.UTC(2026, 9, 5, 9, 30) * 1000;

describe("dates and numbers in the business time zone and locale", () => {
  it("format dates and times in the given zone", () => {
    expect(formatDate(MONDAY_MORNING, { locale: "en-GB", timeZone: "Asia/Tbilisi" })).toBe("5 Oct 2026");
    expect(formatDate(MONDAY_MORNING, { locale: "en-GB", dateStyle: "short", timeZone: "UTC" })).toBe("05/10/2026");
    expect(formatTime(MONDAY_MORNING, { locale: "en-GB", timeZone: "Asia/Tbilisi" })).toBe("13:30");
    expect(formatTime(new Date(MONDAY_MORNING / 1000), { locale: "en-GB", timeZone: "UTC" })).toBe("09:30");
  });

  it("group numbers by the locale", () => {
    expect(formatNumber(1234567, "en")).toBe("1,234,567");
    expect(formatNumber(0.25, "en", { style: "percent" })).toBe("25%");
  });
});

describe("currency digits fallback", () => {
  it("asks Intl for codes the table lacks and defaults to 2 for unknown ones", () => {
    expect(currencyFractionDigits("gel")).toBe(2);
    expect(currencyFractionDigits("XAU")).toBeGreaterThanOrEqual(0);
    expect(currencyFractionDigits("not-a-code")).toBe(2);
  });

  it("shows empty inputs for missing amounts and trims trailing zeros", () => {
    expect(decimalInputValue(null, 2)).toBe("");
    expect(decimalInputValue(undefined, 2)).toBe("");
    expect(decimalInputValue(18.5, 2)).toBe("18.5");
    expect(decimalInputValue(18.499, 2)).toBe("18.5");
  });
});

describe("language names", () => {
  it("read the interface languages from the CLDR table", () => {
    expect(languageName("ka", "ru")).toBe("Грузинский");
    expect(languageName("ka", "ru-RU")).toBe("Грузинский");
  });

  it("ask Intl for other locales and keep the tag when Intl cannot help", () => {
    expect(languageName("de", "fr")).toBe("Allemand");
    expect(languageName("de", "not a locale!")).toBe("de");
  });
});

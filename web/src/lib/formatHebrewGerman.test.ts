/**
 * Dates, money, lists and plurals in Hebrew and German come from the
 * platform's Intl through the cabinet's helpers: Hebrew writes "in" before
 * the month and has a dual ("two") plural, German puts the day first and
 * groups digits with dots.
 */

import { describe, expect, it } from "vitest";

import { textsIn } from "@/test/render";

import { formatDate, formatMoney, formatNumber, formatTime, weekdayName } from "./format";
import { listFormat, pluralRules, relativeTimeFormat } from "./intl/formatters";

// 2026-10-05 09:30 UTC in API microseconds: 12:30 in Jerusalem and 11:30 in Berlin.
const MONDAY_MORNING = Date.UTC(2026, 9, 5, 9, 30) * 1000;

/** Intl's spacing and direction marks are not what a test is about. */
const plain = (text: string) => text.replace(/[  ]/g, " ").replace(/[‎‏]/g, "");

describe("Hebrew", () => {
  it("writes dates, times and money the Israeli way", () => {
    expect(formatDate(MONDAY_MORNING, { locale: "he", timeZone: "Asia/Jerusalem" })).toBe("5 באוק׳ 2026");
    expect(formatTime(MONDAY_MORNING, { locale: "he", timeZone: "Asia/Jerusalem" })).toBe("12:30");
    expect(plain(formatMoney(123450, "ILS", "he"))).toBe("1,234.50 ₪");
    expect(formatNumber(1234567.5, "he")).toBe("1,234,567.5");
    expect(weekdayName(1, "he")).toBe("יום שני");
  });

  it("joins lists, says the day before yesterday and picks the dual plural", () => {
    expect(listFormat("he", { type: "conjunction" }).format(["א", "ב", "ג"])).toBe("א, ב וג");
    expect(listFormat("he", { type: "conjunction" }).format(["WhatsApp", "Telegram"])).toBe("WhatsApp ו-Telegram");
    expect(relativeTimeFormat("he", { numeric: "auto" }).format(-2, "day")).toBe("שלשום");
    expect([1, 2, 3, 20].map((count) => pluralRules("he").select(count))).toEqual(["one", "two", "other", "other"]);
    const texts = textsIn("he");
    expect(texts.tp("settings.requests.conversations", 1)).toBe("שיחה אחת");
    expect(texts.tp("settings.requests.conversations", 2)).toBe("שתי שיחות");
    expect(texts.tp("settings.requests.conversations", 7)).toBe("7 שיחות");
  });
});

describe("German", () => {
  it("writes dates, times and money the German way", () => {
    expect(formatDate(MONDAY_MORNING, { locale: "de", timeZone: "Europe/Berlin" })).toBe("05.10.2026");
    expect(formatTime(MONDAY_MORNING, { locale: "de", timeZone: "Europe/Berlin" })).toBe("11:30");
    expect(plain(formatMoney(123450, "EUR", "de"))).toBe("1.234,50 €");
    expect(formatNumber(1234567.5, "de")).toBe("1.234.567,5");
    expect(weekdayName(1, "de")).toBe("Montag");
  });

  it("joins lists, says the day before yesterday and picks one or other", () => {
    expect(listFormat("de", { type: "conjunction" }).format(["A", "B", "C"])).toBe("A, B und C");
    expect(relativeTimeFormat("de", { numeric: "auto" }).format(-2, "day")).toBe("vorgestern");
    expect([1, 2, 20].map((count) => pluralRules("de").select(count))).toEqual(["one", "other", "other"]);
    const texts = textsIn("de");
    expect(texts.tp("settings.requests.conversations", 1)).toBe("1 Gespräch");
    expect(texts.tp("settings.requests.conversations", 2)).toBe("2 Gespräche");
  });
});

/**
 * Dates, money, lists and plurals in Italian come from the platform's Intl
 * through the cabinet's helpers: the day comes first and the month is a
 * lower-case abbreviation, the decimal mark is a comma, digits group with
 * dots only from five of them on (CLDR's minimumGroupingDigits is 2, so
 * "1234,50 €" but "123.450,50 €"), and the plural has `one`, `other` and,
 * from a million on, `many`.
 */

import { describe, expect, it } from "vitest";

import { textsIn } from "@/test/render";

import { formatDate, formatMoney, formatNumber, formatTime, weekdayName } from "./format";
import { listFormat, pluralRules, relativeTimeFormat } from "./intl/formatters";

// 2026-10-05 09:30 UTC in API microseconds: 11:30 in Rome.
const MONDAY_MORNING = Date.UTC(2026, 9, 5, 9, 30) * 1000;

/** Intl's no-break spaces are not what a test is about. */
const plain = (text: string) => text.replace(/[  ]/g, " ");

describe("Italian", () => {
  it("writes dates, times and money the Italian way", () => {
    expect(formatDate(MONDAY_MORNING, { locale: "it", timeZone: "Europe/Rome" })).toBe("5 ott 2026");
    expect(formatTime(MONDAY_MORNING, { locale: "it", timeZone: "Europe/Rome" })).toBe("11:30");
    // Thousands are grouped from four digits on, as Chrome does (lib/intl/formatters).
    expect(plain(formatMoney(123450, "EUR", "it"))).toBe("1.234,50 €");
    expect(plain(formatMoney(12345050, "EUR", "it"))).toBe("123.450,50 €");
    expect(formatNumber(1234567.5, "it")).toBe("1.234.567,5");
    expect(weekdayName(1, "it")).toBe("lunedì");
  });

  it("joins lists, says the day before yesterday and picks one, other or many", () => {
    expect(listFormat("it", { type: "conjunction" }).format(["a", "b", "c"])).toBe("a, b e c");
    expect(relativeTimeFormat("it", { numeric: "auto" }).format(-2, "day")).toBe("l’altro ieri");
    expect([1, 2, 1_000_000].map((count) => pluralRules("it").select(count))).toEqual(["one", "other", "many"]);
    const texts = textsIn("it");
    expect(texts.tp("settings.requests.conversations", 1)).toBe("1 conversazione");
    expect(texts.tp("settings.requests.conversations", 7)).toBe("7 conversazioni");
  });
});

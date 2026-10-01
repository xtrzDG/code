import { describe, expect, it } from "vitest";

import {
  capitalizeFirst,
  currencyFractionDigits,
  formatDateTime,
  formatMinutesOfDay,
  formatMoney,
  majorToMinor,
  minorToMajor,
  moneyInputProblem,
  parseDecimalInput,
  parseTimeOfDay,
  toDate,
  weekdayName,
} from "./format";

describe("money", () => {
  it("knows the minor units of currencies", () => {
    expect(currencyFractionDigits("GEL")).toBe(2);
    expect(currencyFractionDigits("JPY")).toBe(0);
    expect(currencyFractionDigits("KWD")).toBe(3);
  });

  it("converts between minor and major units", () => {
    expect(minorToMajor(1850, "GEL")).toBe(18.5);
    expect(majorToMinor(18.5, "GEL")).toBe(1850);
    expect(majorToMinor(0.1 + 0.2, "EUR")).toBe(30);
    expect(majorToMinor(1500, "JPY")).toBe(1500);
  });

  it("formats in the interface language", () => {
    expect(formatMoney(1850, "USD", "en")).toBe("$18.50");
    expect(formatMoney(1850, "GEL", "ru")).toMatch(/18,50/);
  });

  it("reads prices typed with either decimal separator", () => {
    expect(parseDecimalInput("18,5", "GEL")).toBe(18.5);
    expect(parseDecimalInput("18.50", "GEL")).toBe(18.5);
    expect(parseDecimalInput("1 200,50", "GEL")).toBe(1200.5);
    expect(parseDecimalInput("1,200.50", "GEL")).toBe(1200.5);
    expect(parseDecimalInput("1.200,50", "GEL")).toBe(1200.5);
    expect(parseDecimalInput("1.200.000", "GEL")).toBe(1200000);
    expect(parseDecimalInput("", "GEL")).toBeNull();
    expect(parseDecimalInput("abc", "GEL")).toBeNull();
    expect(parseDecimalInput("-5", "GEL")).toBeNull();
  });

  it("reads one separator before three digits as grouping for currencies without decimals", () => {
    expect(parseDecimalInput("1,200", "JPY")).toBe(1200);
    expect(parseDecimalInput("10.000", "KRW")).toBe(10000);
    expect(parseDecimalInput("1.255", "KWD")).toBe(1.255);
    expect(parseDecimalInput("0,500", "USD")).toBe(0.5);
  });

  it("refuses prices that would be stored at the wrong amount", () => {
    // Thousands or decimals? Refused rather than stored 1000 times too low.
    expect(moneyInputProblem("25.000", "IDR")).toBe("ambiguous");
    expect(moneyInputProblem("1.000", "BRL")).toBe("ambiguous");
    expect(moneyInputProblem("1,200", "USD")).toBe("ambiguous");
    expect(moneyInputProblem("1.500", "EUR")).toBe("ambiguous");
    expect(moneyInputProblem("0,505", "USD")).toBe("precision");
    expect(moneyInputProblem("0,500", "USD")).toBeNull();
    expect(moneyInputProblem("1200,5", "JPY")).toBe("precision");
    expect(moneyInputProblem("abc", "USD")).toBe("number");
    // Unambiguous forms pass.
    expect(moneyInputProblem("1,500", "JPY")).toBeNull();
    expect(moneyInputProblem("1.255", "KWD")).toBeNull();
    expect(moneyInputProblem("25.000,00", "IDR")).toBeNull();
    expect(moneyInputProblem("1.200.000", "COP")).toBeNull();
    expect(moneyInputProblem("18,50", "GEL")).toBeNull();
    expect(moneyInputProblem("1200", "USD")).toBeNull();
    expect(moneyInputProblem("1500.00", "JPY")).toBeNull();
  });
});

describe("dates and times", () => {
  it("reads API microseconds", () => {
    expect(toDate(1_700_000_000_000_000).toISOString()).toBe("2023-11-14T22:13:20.000Z");
  });

  it("formats in the business time zone", () => {
    const text = formatDateTime(Date.UTC(2026, 9, 1, 8, 30) * 1000, {
      locale: "en-GB",
      timeZone: "Asia/Tbilisi",
      dateStyle: "short",
    });
    expect(text).toContain("12:30");
  });

  it("converts minutes of the day", () => {
    expect(formatMinutesOfDay(0)).toBe("00:00");
    expect(formatMinutesOfDay(1080)).toBe("18:00");
    expect(formatMinutesOfDay(1440)).toBe("24:00");
    expect(parseTimeOfDay("9:05")).toBe(545);
    expect(parseTimeOfDay("24:00")).toBeNull();
    expect(parseTimeOfDay("")).toBeNull();
  });

  it("names ISO weekdays", () => {
    expect(weekdayName(1, "en")).toBe("Monday");
    expect(weekdayName(7, "en", "short")).toBe("Sun");
  });
});

describe("labels", () => {
  it("capitalizes the first letter, but never turns Georgian into Mtavruli", () => {
    expect(capitalizeFirst("русский", "ru")).toBe("Русский");
    expect(capitalizeFirst("ქართული", "ka")).toBe("ქართული");
    expect(capitalizeFirst("", "en")).toBe("");
  });
});

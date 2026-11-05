import { describe, expect, it } from "vitest";

import { splitInternationalNumber } from "./internationalNumber";

const country = (code: string, callingCode: number, status: "supported" | "pilot" | "restricted" = "supported") => ({
  country_code: code,
  calling_code: callingCode,
  onboarding_status: status,
});

const COUNTRIES = [
  country("IT", 39, "pilot"),
  country("VA", 39),
  country("US", 1),
  country("CA", 1),
  country("BS", 1242),
  country("GE", 995),
  country("RU", 7, "restricted"),
  country("KZ", 7),
];

describe("a number typed with its calling code", () => {
  it("picks the country of the code and keeps the digits after it", () => {
    expect(splitInternationalNumber("+393514432225", COUNTRIES, null)).toEqual({ countryCode: "IT", nationalNumber: "3514432225" });
    expect(splitInternationalNumber("+39 351 443 2225", COUNTRIES, "US")).toEqual({ countryCode: "IT", nationalNumber: "351 443 2225" });
    expect(splitInternationalNumber("00995 32 212 34 56", COUNTRIES, null)).toEqual({ countryCode: "GE", nationalNumber: "32 212 34 56" });
  });

  it("keeps the chosen country when several share the code, else an available one", () => {
    expect(splitInternationalNumber("+1 416 555 0100", COUNTRIES, "CA")?.countryCode).toBe("CA");
    expect(splitInternationalNumber("+1 416 555 0100", COUNTRIES, "IT")?.countryCode).toBe("US");
    expect(splitInternationalNumber("+7 701 000 00 00", COUNTRIES, null)?.countryCode).toBe("KZ");
    expect(splitInternationalNumber("+7 701 000 00 00", COUNTRIES, "RU")?.countryCode).toBe("RU");
  });

  it("prefers the longest code the digits start with", () => {
    expect(splitInternationalNumber("+1242 555 0100", COUNTRIES, null)).toEqual({ countryCode: "BS", nationalNumber: "555 0100" });
    expect(splitInternationalNumber("+124", COUNTRIES, null)).toEqual({ countryCode: "US", nationalNumber: "24" });
  });

  it("is empty while only the code is typed and null for a national number or an unknown code", () => {
    expect(splitInternationalNumber("+39", COUNTRIES, null)).toEqual({ countryCode: "IT", nationalNumber: "" });
    expect(splitInternationalNumber("+", COUNTRIES, null)).toBeNull();
    expect(splitInternationalNumber("+3", COUNTRIES, null)).toBeNull();
    expect(splitInternationalNumber("351 443 2225", COUNTRIES, "IT")).toBeNull();
    expect(splitInternationalNumber("+39 abc", COUNTRIES, null)).toBeNull();
  });
});

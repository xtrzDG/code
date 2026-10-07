import { describe, expect, it } from "vitest";

import { ApiError } from "@/api/errors";
import type { CountryListItem } from "@/api/types";

import {
  buildOtpStartBody,
  classifyOtpStartError,
  classifyOtpVerifyError,
  countryFlag,
  countryOptionLabel,
  filterCountries,
  formatCallingCode,
  guessCountryCode,
  hasInternationalPrefix,
  isCountryAvailable,
  looksLikeEmail,
  looksLikePhoneNumber,
  pickInitialTimezone,
  toAsciiDigits,
} from "./countries";

function country(overrides: Partial<CountryListItem>): CountryListItem {
  return {
    country_code: "GE",
    display_name: "Georgia",
    english_name: "Georgia",
    calling_code: 995,
    currency_code: "GEL",
    default_timezone: "Asia/Tbilisi",
    default_owner_language: "ka",
    has_price_book: false,
    onboarding_status: "supported",
    ...overrides,
  };
}

const COUNTRIES = [
  country({}),
  country({ country_code: "AM", display_name: "Армения", english_name: "Armenia", calling_code: 374 }),
  country({ country_code: "US", display_name: "США", english_name: "United States", calling_code: 1 }),
  country({ country_code: "KP", display_name: "КНДР", english_name: "North Korea", calling_code: 850, onboarding_status: "restricted" }),
];

describe("country presentation", () => {
  it("builds flags and calling codes", () => {
    expect(countryFlag("ge")).toBe("🇬🇪");
    expect(countryFlag("1")).toBe("");
    expect(formatCallingCode(995)).toBe("+995");
  });

  it("labels options and marks restricted countries", () => {
    expect(countryOptionLabel(COUNTRIES[0]!)).toBe("🇬🇪 Georgia (+995)");
    expect(isCountryAvailable(COUNTRIES[3]!)).toBe(false);
    expect(countryOptionLabel(COUNTRIES[3]!, "not available yet")).toContain("— not available yet");
  });

  it("finds countries by local name, English name, code and calling code", () => {
    expect(filterCountries(COUNTRIES, "арм").map((item) => item.country_code)).toEqual(["AM"]);
    expect(filterCountries(COUNTRIES, "united").map((item) => item.country_code)).toEqual(["US"]);
    expect(filterCountries(COUNTRIES, "ge").map((item) => item.country_code)).toContain("GE");
    expect(filterCountries(COUNTRIES, "+37").map((item) => item.country_code)).toEqual(["AM"]);
    expect(filterCountries(COUNTRIES, " ")).toHaveLength(4);
  });
});

describe("guessCountryCode", () => {
  const available = ["GE", "AM", "US", "DE"];

  it("uses the region of the browser language", () => {
    expect(guessCountryCode(["en-US", "ka"], available)).toBe("US");
    expect(guessCountryCode(["hy-AM"], available)).toBe("AM");
  });

  it("maps region-less languages to their country", () => {
    expect(guessCountryCode(["ka"], available)).toBe("GE");
    expect(guessCountryCode(["de"], available)).toBe("DE");
  });

  it("falls back to the first market, then to any available country", () => {
    expect(guessCountryCode(["ru"], available)).toBe("GE");
    expect(guessCountryCode(["ru"], ["US", "AM"])).toBe("US");
    expect(guessCountryCode([], [])).toBeNull();
  });

  it("ignores regions that are not available", () => {
    expect(guessCountryCode(["en-KP", "hy"], available)).toBe("AM");
  });
});

describe("phone input checks", () => {
  it("accepts numbers of any country in common formats", () => {
    expect(looksLikePhoneNumber("+995 555 12-34-56")).toBe(true);
    expect(looksLikePhoneNumber("8 (999) 123-45-67")).toBe(true);
    expect(looksLikePhoneNumber("555123456")).toBe(true);
  });

  it("rejects text and too short or too long numbers", () => {
    expect(looksLikePhoneNumber("call me")).toBe(false);
    expect(looksLikePhoneNumber("123")).toBe(false);
    expect(looksLikePhoneNumber("1".repeat(18))).toBe(false);
  });

  it("detects international prefixes", () => {
    expect(hasInternationalPrefix(" +1 202")).toBe(true);
    expect(hasInternationalPrefix("00995")).toBe(true);
    expect(hasInternationalPrefix("555")).toBe(false);
  });

  it("checks e-mail addresses loosely", () => {
    expect(looksLikeEmail("owner@cafe.ge")).toBe(true);
    expect(looksLikeEmail("owner@cafe")).toBe(false);
  });
});

describe("OTP request body", () => {
  it("sends the phone as typed with the chosen country", () => {
    expect(
      buildOtpStartBody({ method: "phone", phoneNumber: " 555 12 34 56 ", email: "", countryCode: "GE", locale: "ka" }),
    ).toEqual({ phone_number: "555 12 34 56", country_hint: "GE", locale: "ka" });
  });

  it("sends only the e-mail for e-mail sign-in", () => {
    expect(
      buildOtpStartBody({ method: "email", phoneNumber: "555", email: " a@b.ge ", countryCode: "GE", locale: "en" }),
    ).toEqual({ email: "a@b.ge", locale: "en" });
  });
});

describe("OTP error classification", () => {
  const error = (status: number, code: ApiError["code"], detail?: string) => new ApiError({ status, code, detail });

  it("explains refused code requests", () => {
    expect(classifyOtpStartError(error(403, "access_denied"), "phone")).toBe("countryRestricted");
    expect(classifyOtpStartError(error(429, "rate_limited"), "email")).toBe("resendTooSoon");
    expect(
      classifyOtpStartError(error(422, "validation_failed", "This number cannot receive login codes; use a mobile number."), "phone"),
    ).toBe("cannotReceive");
    expect(classifyOtpStartError(error(422, "validation_failed", "Not a phone number"), "phone")).toBe("phoneInvalid");
    expect(classifyOtpStartError(error(422, "validation_failed"), "email")).toBe("emailInvalid");
    expect(classifyOtpStartError(error(502, "external_service_error"), "phone")).toBeNull();
  });

  it("explains refused codes", () => {
    expect(classifyOtpVerifyError(error(401, "authentication_required"))).toBe("wrongCode");
    expect(classifyOtpVerifyError(error(429, "rate_limited"))).toBe("tooManyAttempts");
    expect(classifyOtpVerifyError(error(0, "network_error"))).toBeNull();
  });
});

describe("phone input in any script", () => {
  it.each([
    "٠٥٠١٢٣٤٥٦٧",
    "۰۹۱۲۳۴۵۶۷۸۹",
    "\u202A+995 555 12 34 56\u202C",
    "\u200E+995 555 12 34 56",
    "+995\u2011555\u201112\u201134\u201156",
    "＋９９５ ５５５ １２ ３４ ５６",
  ])("accepts %j", (raw) => {
    expect(looksLikePhoneNumber(raw)).toBe(true);
  });

  it("maps digits of any script to ASCII", () => {
    expect(toAsciiDigits("١٢٣٤٥٦")).toBe("123456");
    expect(toAsciiDigits("۱۲۳۴۵۶")).toBe("123456");
    expect(toAsciiDigits("１２３４５６")).toBe("123456");
    expect(toAsciiDigits("०९८७६५")).toBe("098765");
    expect(toAsciiDigits("\u202A+995 555\u202C")).toBe("+995 555");
  });

  it("still rejects text and too few digits", () => {
    expect(looksLikePhoneNumber("call me")).toBe(false);
    expect(looksLikePhoneNumber("١٢٣")).toBe(false);
  });
});

describe("pickInitialTimezone", () => {
  const RUSSIA = ["Europe/Kaliningrad", "Europe/Moscow", "Asia/Yekaterinburg", "Asia/Vladivostok"];

  it("takes the browser zone when the country has it", () => {
    expect(pickInitialTimezone(RUSSIA, "Europe/Moscow", "Asia/Vladivostok")).toBe("Asia/Vladivostok");
  });

  it("keeps the country default for a browser elsewhere", () => {
    expect(pickInitialTimezone(RUSSIA, "Europe/Moscow", "Asia/Tbilisi")).toBe("Europe/Moscow");
    expect(pickInitialTimezone(RUSSIA, "Europe/Moscow", null)).toBe("Europe/Moscow");
  });
});

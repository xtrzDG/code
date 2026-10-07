import { describe, expect, it } from "vitest";

import type { CountryListItem } from "@/api/types";

import { countryChoices } from "./countryChoices";

const COUNTRY: CountryListItem = {
  country_code: "GE",
  display_name: "Georgia",
  english_name: "Georgia",
  calling_code: 995,
  currency_code: "GEL",
  default_timezone: "Asia/Tbilisi",
  default_owner_language: "ka",
  onboarding_status: "supported",
  has_price_book: true,
};

describe("the price picker's countries", () => {
  it("carry the code, the flag with the page's name and whether they can be chosen", () => {
    expect(
      countryChoices([COUNTRY, { ...COUNTRY, country_code: "XK", display_name: "Kosovo", onboarding_status: "restricted" }]),
    ).toEqual([
      { code: "GE", label: "🇬🇪 Georgia", isAvailable: true },
      { code: "XK", label: "🇽🇰 Kosovo", isAvailable: false },
    ]);
  });

  it("keep the catalog's order and nothing else of its entries", () => {
    const choices = countryChoices([{ ...COUNTRY, country_code: "AM", display_name: "Armenia" }, COUNTRY]);
    expect(choices.map((choice) => choice.code)).toEqual(["AM", "GE"]);
    expect(Object.keys(choices[0] ?? {}).sort()).toEqual(["code", "isAvailable", "label"]);
  });
});

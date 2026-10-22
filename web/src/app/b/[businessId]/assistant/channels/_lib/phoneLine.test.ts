import { describe, expect, it } from "vitest";

import type { CountryListItem } from "@/api/types";

import {
  cityQuery,
  groupCountries,
  initialCountry,
  numberInText,
  rentBody,
  rentedNumberState,
  teamArrangesReason,
  type PhoneLineView,
  type PhoneNumberOffers,
  type RentedPhoneNumber,
} from "./phoneLine";

function country(code: string, name: string): CountryListItem {
  return {
    country_code: code,
    display_name: name,
    english_name: name,
    calling_code: 1,
    currency_code: "USD",
    default_owner_language: "en",
    default_timezone: "UTC",
    has_price_book: false,
    onboarding_status: "supported",
  } as CountryListItem;
}

const COUNTRIES = [country("AM", "Armenia"), country("GE", "Georgia"), country("US", "United States")];

const LINE: PhoneLineView = {
  business_id: "business_1",
  are_numbers_self_serve: true,
  self_serve_countries: ["US"],
  default_country_code: "GE",
};

const OFFERS: PhoneNumberOffers = {
  country_code: "US",
  number_type: "local",
  availability: "self_serve",
  monthly_price: { money: { amount_minor: 500, currency_code: "GEL" }, text: "5.00 ₾", is_estimated: false },
  offers: [{ phone_number: "+15125550142", display_number: "+1 512-555-0142", locality: "Austin", region: "TX" }],
};

const RENTED: RentedPhoneNumber = {
  phone_number: "+15125550142",
  display_number: "+1 512-555-0142",
  country_code: "US",
  number_type: "local",
  monthly_price: { money: { amount_minor: 500, currency_code: "GEL" }, text: "5.00 ₾", is_estimated: false },
  status: "active",
  is_attached: true,
  rented_at: 1,
};

describe("the phone line", () => {
  it("lists the countries where a number is taken at once first, the rest after", () => {
    const groups = groupCountries(COUNTRIES, ["us"]);

    expect(groups.now.map((item) => item.country_code)).toEqual(["US"]);
    expect(groups.team.map((item) => item.country_code)).toEqual(["AM", "GE"]);
  });

  it("opens the search in the business's own country", () => {
    expect(initialCountry(LINE, COUNTRIES)).toBe("GE");
    expect(initialCountry(LINE, [])).toBe("GE");
    expect(initialCountry({ ...LINE, default_country_code: "ZZ" }, COUNTRIES)).toBe("US");
  });

  it("takes an offer at the price the owner saw", () => {
    expect(rentBody(OFFERS.offers![0]!, OFFERS)).toEqual({
      phone_number: "+15125550142",
      number_type: "local",
      monthly_price: { amount_minor: 500, currency_code: "GEL" },
      locality: "Austin",
    });
    expect(rentBody(OFFERS.offers![0]!, { ...OFFERS, monthly_price: null })).toBeNull();
  });

  it("says whether a rented number answers yet or is going back", () => {
    expect(rentedNumberState(RENTED)).toBe("phoneNumbers.panel.answering");
    expect(rentedNumberState({ ...RENTED, is_attached: false })).toBe("phoneNumbers.panel.connecting");
    expect(rentedNumberState({ ...RENTED, status: "releasing" })).toBe("phoneNumbers.panel.releasing");
  });

  it("explains why the team arranges a number", () => {
    expect(teamArrangesReason("requires_documents")).toBe("phoneNumbers.request.requires_documents");
    expect(teamArrangesReason("on_request")).toBe("phoneNumbers.request.on_request");
    expect(teamArrangesReason("self_serve")).toBeNull();
  });

  it("keeps a number in a sentence left to right", () => {
    expect(numberInText("+1 512-555-0142")).toBe("\u2066+1 512-555-0142\u2069");
  });

  it("searches near a city only when one is written", () => {
    expect(cityQuery("  Austin ")).toBe("Austin");
    expect(cityQuery("   ")).toBeUndefined();
  });
});

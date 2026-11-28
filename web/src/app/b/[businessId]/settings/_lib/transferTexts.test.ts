import { describe, expect, it } from "vitest";

import { en } from "@/i18n/messages/en";
import { it as italian } from "@/i18n/messages/it";
import { createTranslator } from "@/i18n/translate";

import { EU_COUNTRY_CODES, transferTexts } from "./transferTexts";

const ITALIAN_LAW = /Italian labour law|Workers' Statute|diritto del lavoro italiano|Statuto dei lavoratori/;
const ANOTHER_EU_COUNTRY = /another EU country|altro paese dell'UE/;

describe("the transfer texts follow the business's country", () => {
  it("name the Italian labour law and link the notice template only for a business in Italy", () => {
    expect(transferTexts("IT")).toEqual({
      description: "callSettings.transfers.descriptionItaly",
      numberRule: "callSettings.transfers.numberRuleEu",
      noticeTemplate: "staff-call-notice",
    });
  });

  it("keep 'another EU country' for a business elsewhere in the EU, without the Italian law", () => {
    for (const country of ["DE", "FR", "RO"]) {
      expect(transferTexts(country), country).toEqual({
        description: "callSettings.transfers.description",
        numberRule: "callSettings.transfers.numberRuleEu",
        noticeTemplate: null,
      });
    }
  });

  it("say 'an EU country' to a business outside the EU", () => {
    for (const country of ["US", "CA", "GE", "GB", "CH", ""]) {
      expect(transferTexts(country), country).toEqual({
        description: "callSettings.transfers.description",
        numberRule: "callSettings.transfers.numberRule",
        noticeTemplate: null,
      });
    }
  });

  it("know the 27 member states of the API's rule", () => {
    expect(EU_COUNTRY_CODES.size).toBe(27);
    expect(EU_COUNTRY_CODES.has("IT")).toBe(true);
    expect(EU_COUNTRY_CODES.has("GB")).toBe(false);
  });

  it.each([
    ["en", en],
    ["it", italian],
  ] as const)("read in %s without Italy or the EU where they do not apply", (locale, messages) => {
    const { t } = createTranslator(locale, messages);
    const read = (country: string) => {
      const texts = transferTexts(country);
      return { description: t(texts.description), numberRule: t(texts.numberRule) };
    };

    expect(read("IT").description).toMatch(ITALIAN_LAW);
    expect(read("IT").numberRule).toMatch(ANOTHER_EU_COUNTRY);
    expect(read("DE").description).not.toMatch(ITALIAN_LAW);
    expect(read("DE").numberRule).toMatch(ANOTHER_EU_COUNTRY);
    expect(read("US").description).not.toMatch(ITALIAN_LAW);
    expect(read("US").numberRule).not.toMatch(ANOTHER_EU_COUNTRY);
    expect(read("US").numberRule).toMatch(/EU|UE/);
  });
});

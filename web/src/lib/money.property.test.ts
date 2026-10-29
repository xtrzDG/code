import fc from "fast-check";
import { describe, expect, it } from "vitest";

import { propertyParameters } from "@/test/properties";

import { CURRENCY_MINOR_DIGITS } from "./currencyDigits.generated";
import { currencyFractionDigits, decimalInputValue, majorToMinor, minorToMajor, moneyInputProblem, parseDecimalInput } from "./format";

const CURRENCIES = Object.keys(CURRENCY_MINOR_DIGITS);
/** A trillion minor units: far above any price, well inside exact doubles. */
const MAX_MINOR = 1_000_000_000_000;

const currencies = fc.constantFrom(...CURRENCIES);
const amounts = fc.integer({ min: 0, max: MAX_MINOR });

/** Thousands grouped the way people type them: "1 234 567,5". */
function grouped(text: string, separator: string): string {
  const [whole = "", fraction] = text.split(".");
  const groups = whole.replace(/\B(?=(\d{3})+(?!\d))/g, separator);
  return fraction === undefined ? groups : `${groups},${fraction}`;
}

describe("money round trips in every currency (property)", () => {
  it("knows the precision of every currency the backend uses", () => {
    expect(CURRENCIES.length).toBeGreaterThan(150);
    expect(new Set(CURRENCIES.map(currencyFractionDigits))).toEqual(new Set([0, 2, 3, 4]));
  });

  it("keeps minor units through major units and back", () => {
    fc.assert(
      fc.property(currencies, amounts, (currency, minor) => majorToMinor(minorToMajor(minor, currency), currency) === minor),
      propertyParameters(),
    );
  });

  it("reads back what a price field shows, without a problem", () => {
    fc.assert(
      fc.property(currencies, amounts, (currency, minor) => {
        const text = decimalInputValue(minorToMajor(minor, currency), currencyFractionDigits(currency));
        const parsed = parseDecimalInput(text, currency);
        return parsed !== null && majorToMinor(parsed, currency) === minor && moneyInputProblem(text, currency) === null;
      }),
      propertyParameters(),
    );
  });

  it("reads a price typed with space-grouped thousands and a decimal comma the same way", () => {
    fc.assert(
      fc.property(currencies, amounts, fc.constantFrom(" ", " ", " "), (currency, minor, space) => {
        const plain = decimalInputValue(minorToMajor(minor, currency), currencyFractionDigits(currency));
        const typed = grouped(plain, space);
        const parsed = parseDecimalInput(typed, currency);
        return parsed !== null && majorToMinor(parsed, currency) === minor;
      }),
      propertyParameters(),
    );
  });
});

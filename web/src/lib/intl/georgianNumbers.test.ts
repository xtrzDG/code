import { describe, expect, it } from "vitest";

import { listFormat, numberFormat, pluralRules, relativeTimeFormat } from "./formatters";
import { georgianNumberFormat } from "./georgianNumbers";

// Node ships full ICU (`npm run check:intl`): its Georgian is the reference.
const VALUES = [0, -0, 1, 5, 12.345, 999, 1000, 1234, 9999, 10_000, 12_345, 123_456.5, 1_234_567.891, -1234.5, -12_345, 1e21, 0.0072, 0.375, Number.NaN, Infinity, -Infinity];

const OPTION_SETS: Intl.NumberFormatOptions[] = [
  {},
  { maximumFractionDigits: 0 },
  { maximumFractionDigits: 1 },
  { minimumFractionDigits: 1, maximumFractionDigits: 1 },
  { minimumFractionDigits: 2, maximumFractionDigits: 4 },
  { useGrouping: false },
  { useGrouping: "always" },
  { style: "percent" },
  { style: "percent", maximumFractionDigits: 0 },
  { style: "percent", maximumFractionDigits: 1 },
  { style: "currency", currency: "GEL" },
  { style: "currency", currency: "GEL", minimumFractionDigits: 2, maximumFractionDigits: 2 },
  { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 4 },
  { style: "currency", currency: "JPY", minimumFractionDigits: 0, maximumFractionDigits: 0 },
  { style: "currency", currency: "EUR", currencyDisplay: "symbol" },
  { style: "currency", currency: "KWD" },
];

describe("Georgian numbers", () => {
  it("are written as Node's ICU writes them", () => {
    for (const options of OPTION_SETS) {
      const ours = georgianNumberFormat(options);
      expect(ours, JSON.stringify(options)).not.toBeNull();
      const reference = new Intl.NumberFormat("ka", options);
      for (const value of VALUES) {
        expect(ours!(value), `${JSON.stringify(options)} ${value}`).toBe(reference.format(value));
      }
    }
  });

  it("show every currency with the sign or code Georgian uses", () => {
    for (const currency of Intl.supportedValuesOf("currency")) {
      const options: Intl.NumberFormatOptions = { style: "currency", currency };
      expect(georgianNumberFormat(options)!(1234.5), currency).toBe(new Intl.NumberFormat("ka", options).format(1234.5));
    }
  });

  it("leave units, compact numbers and accounting signs to the platform", () => {
    for (const options of [
      { style: "unit", unit: "kilometer" },
      { notation: "compact" },
      { style: "currency", currency: "GEL", currencyDisplay: "name" },
      { style: "currency", currency: "GEL", currencySign: "accounting" },
      { signDisplay: "always" },
    ] as Intl.NumberFormatOptions[]) {
      expect(georgianNumberFormat(options), JSON.stringify(options)).toBeNull();
      expect(numberFormat("ka", options).format(-1234.5)).toBe(new Intl.NumberFormat("ka", options).format(-1234.5));
    }
  });

  it("are the factory's for Georgian tags only", () => {
    expect(numberFormat("ka-GE", { style: "currency", currency: "GEL" }).format(18.5)).toBe("18,50 ₾");
    expect(numberFormat("ru").format(1234.5)).toBe(new Intl.NumberFormat("ru").format(1234.5));
    expect(numberFormat("en").format(1234.5)).toBe("1,234.5");
  });
});

describe("Georgian relative times", () => {
  const UNITS: Intl.RelativeTimeFormatUnit[] = ["second", "minute", "hour", "day", "week", "month", "quarter", "year", "days", "hours"];

  it("are written as Node's ICU writes them", () => {
    for (const numeric of ["auto", "always"] as const) {
      const ours = relativeTimeFormat("ka", { numeric });
      const reference = new Intl.RelativeTimeFormat("ka", { numeric });
      for (const unit of UNITS) {
        for (const value of [-12_345, -21, -3, -2, -1.5, -1, -0, 0, 1, 2, 3, 21, 12_345]) {
          expect(ours.format(value, unit), `${numeric} ${value} ${unit}`).toBe(reference.format(value, unit));
        }
      }
    }
  });

  it("refuse an unknown unit like the platform", () => {
    expect(() => relativeTimeFormat("ka").format(1, "fortnight" as Intl.RelativeTimeFormatUnit)).toThrow(RangeError);
  });

  it("leave other languages to the platform", () => {
    expect(relativeTimeFormat("ru", { numeric: "auto" }).format(-1, "day")).toBe("вчера");
  });
});

describe("Georgian lists and plural forms", () => {
  it("join lists as Node's ICU does", () => {
    for (const type of ["conjunction", "disjunction", "unit"] as const) {
      for (const items of [[], ["ა"], ["ა", "ბ"], ["ა", "ბ", "გ"], ["ა", "ბ", "გ", "დ"]]) {
        expect(listFormat("ka", { type }).format(items), `${type} ${items.length}`).toBe(
          new Intl.ListFormat("ka", { type }).format(items),
        );
      }
    }
    expect(listFormat("ka").format(["ა", "ბ"])).toBe("ა და ბ");
    expect(listFormat("ru", { type: "conjunction" }).format(["а", "б"])).toBe("а и б");
  });

  it("pick the plural form as Node's ICU does", () => {
    const reference = new Intl.PluralRules("ka");
    for (const value of [-2, -1, 0, 1, 1.5, 2, 5, 11, 21, 101]) {
      expect(pluralRules("ka").select(value), String(value)).toBe(reference.select(value));
    }
    expect(pluralRules("ru").select(3)).toBe("few");
  });
});

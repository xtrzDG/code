/**
 * Georgian numbers, lists, relative times and plural forms as CLDR writes
 * them ("12 345,50 ₾", "38%", "a, b და c", "გუშინ", "5 საათის წინ"), built
 * on the English Intl every browser has. See `georgianData.ts` for why.
 */

import {
  CURRENCY_SYMBOLS,
  LIST_WORDS,
  NO_BREAK_SPACE,
  NOT_A_NUMBER,
  RELATIVE_WORDS,
  type RelativeUnit,
} from "./georgianData";

/** Georgian groups thousands only from five digits on: "1234", "12 345". */
const MINIMUM_GROUPED_DIGITS = 5;

type Grouping = "none" | "always" | "min2";

function groupingOf(useGrouping: Intl.NumberFormatOptions["useGrouping"]): Grouping {
  const value: unknown = useGrouping;
  if (value === false || value === "false") {
    return "none";
  }
  return value === "always" ? "always" : "min2";
}

function groupDigits(integer: string, grouping: Grouping): string {
  if (grouping === "none" || integer.length < (grouping === "always" ? 4 : MINIMUM_GROUPED_DIGITS)) {
    return integer;
  }
  return integer.replace(/\B(?=(\d{3})+(?!\d))/g, NO_BREAK_SPACE);
}

/** Whether the Georgian number format covers these options (else the browser's own Intl is asked). */
function isSupported(options: Intl.NumberFormatOptions): boolean {
  return (
    (options.style === undefined || ["decimal", "percent", "currency"].includes(options.style)) &&
    (options.notation === undefined || options.notation === "standard") &&
    (options.currencyDisplay === undefined || options.currencyDisplay === "symbol") &&
    (options.currencySign === undefined || options.currencySign === "standard") &&
    (options.signDisplay === undefined || options.signDisplay === "auto")
  );
}

/** A Georgian number formatter, or null for options it does not cover (units, compact notation). */
export function georgianNumberFormat(options: Intl.NumberFormatOptions = {}): ((value: number) => string) | null {
  if (!isSupported(options)) {
    return null;
  }
  // English digits, rounding and currency precision; Georgian separators and signs.
  const english = new Intl.NumberFormat("en-US", { ...options, currencyDisplay: "code", useGrouping: false });
  const grouping = groupingOf(options.useGrouping);
  return (value) => {
    let sign = "";
    let integer = "";
    let fraction = "";
    let special = "";
    let currency = "";
    let isPercent = false;
    for (const part of english.formatToParts(value)) {
      switch (part.type) {
        case "minusSign":
          sign = "-";
          break;
        case "integer":
          integer += part.value;
          break;
        case "fraction":
          fraction += part.value;
          break;
        case "nan":
          special = NOT_A_NUMBER;
          break;
        case "infinity":
          special = "∞";
          break;
        case "currency":
          currency = part.value;
          break;
        case "percentSign":
          isPercent = true;
          break;
        default:
          break;
      }
    }
    const number = special || `${groupDigits(integer, grouping)}${fraction ? `,${fraction}` : ""}`;
    const percent = isPercent ? "%" : "";
    const money = currency ? `${NO_BREAK_SPACE}${CURRENCY_SYMBOLS[currency] ?? currency}` : "";
    return `${sign}${number}${percent}${money}`;
  };
}

/** "a, b და c" (conjunction), "a, b ან c" (disjunction), "a, b, c" (unit). */
export function formatGeorgianList(items: readonly string[], type: Intl.ListFormatType = "conjunction"): string {
  if (items.length < 2) {
    return items[0] ?? "";
  }
  if (type === "unit") {
    return items.join(", ");
  }
  return `${items.slice(0, -1).join(", ")} ${LIST_WORDS[type]} ${items[items.length - 1]}`;
}

function relativeUnit(unit: Intl.RelativeTimeFormatUnit): RelativeUnit {
  const singular = unit.endsWith("s") ? unit.slice(0, -1) : unit;
  if (!(singular in RELATIVE_WORDS)) {
    throw new RangeError(`Invalid unit argument for format() '${unit}'`);
  }
  return singular as RelativeUnit;
}

/** "5 საათის წინ", "5 საათში"; with numeric "auto" also "გუშინ", "ახლა". */
export function georgianRelativeTimeFormat(
  options: Intl.RelativeTimeFormatOptions = {},
): (value: number, unit: Intl.RelativeTimeFormatUnit) => string {
  const number = georgianNumberFormat()!;
  return (value, unit) => {
    const words = RELATIVE_WORDS[relativeUnit(unit)];
    const named = options.numeric === "auto" ? words.named[value] : undefined;
    if (named !== undefined) {
      return named;
    }
    const isPast = value < 0 || Object.is(value, -0);
    return `${number(Math.abs(value))} ${isPast ? words.past : words.future}`;
  };
}

/** CLDR plural categories of Georgian: "one" for 1, "other" for everything else. */
export function georgianPluralCategory(value: number): Intl.LDMLPluralRule {
  return Math.abs(value) === 1 ? "one" : "other";
}

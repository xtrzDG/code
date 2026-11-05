/**
 * Georgian calendar and number words of CLDR (as ICU 77 ships them in
 * Node), for the Georgian formatters in `georgian*.ts`. Chrome's Intl has
 * no Georgian at all and formats "ka" as American English; these tables
 * let the cabinet show Georgian dates and numbers in every browser, and the
 * same text on the server and in the browser. `georgian.test.ts` compares
 * each formatter with Node's own Intl.
 */

export const NO_BREAK_SPACE = " ";

/** Month names, January first. */
export const MONTHS_LONG = [
  "იანვარი",
  "თებერვალი",
  "მარტი",
  "აპრილი",
  "მაისი",
  "ივნისი",
  "ივლისი",
  "აგვისტო",
  "სექტემბერი",
  "ოქტომბერი",
  "ნოემბერი",
  "დეკემბერი",
] as const;

export const MONTHS_SHORT = ["იან", "თებ", "მარ", "აპრ", "მაი", "ივნ", "ივლ", "აგვ", "სექ", "ოქტ", "ნოე", "დეკ"] as const;

/** Weekday names, Sunday first (as `Date#getUTCDay` counts). */
export const WEEKDAYS_LONG = ["კვირა", "ორშაბათი", "სამშაბათი", "ოთხშაბათი", "ხუთშაბათი", "პარასკევი", "შაბათი"] as const;

export const WEEKDAYS_SHORT = ["კვი", "ორშ", "სამ", "ოთხ", "ხუთ", "პარ", "შაბ"] as const;

/** Currency signs Georgian writes; every other currency shows its code ("1500 JPY"). */
export const CURRENCY_SYMBOLS: Readonly<Record<string, string>> = {
  BRL: "R$",
  CAD: "CA$",
  EUR: "€",
  GBP: "£",
  GEL: "₾",
  MXN: "MX$",
  TWD: "NT$",
  USD: "US$",
  XAF: "FCFA",
  XCD: "EC$",
  XCG: "Cg.",
  XOF: "F\u202fCFA",
  XPF: "CFPF",
};

/** "Not a number", as Georgian number formats write NaN. */
export const NOT_A_NUMBER = `არ${NO_BREAK_SPACE}არის${NO_BREAK_SPACE}რიცხვი`;

export const LIST_WORDS = { conjunction: "და", disjunction: "ან" } as const;

export type RelativeUnit = "second" | "minute" | "hour" | "day" | "week" | "month" | "quarter" | "year";

interface RelativeWords {
  /** After the number: "5 საათის წინ" (5 hours ago). */
  past: string;
  /** After the number: "5 საათში" (in 5 hours). */
  future: string;
  /** Words without a number for `numeric: "auto"`: -1 is "yesterday" for days. */
  named: Readonly<Record<number, string>>;
}

export const RELATIVE_WORDS: Readonly<Record<RelativeUnit, RelativeWords>> = {
  second: { past: "წამის წინ", future: "წამში", named: { 0: "ახლა" } },
  minute: { past: "წუთის წინ", future: "წუთში", named: { 0: "ამ წუთში" } },
  hour: { past: "საათის წინ", future: "საათში", named: { 0: "ამ საათში" } },
  day: {
    past: "დღის წინ",
    future: "დღეში",
    named: { [-2]: "გუშინწინ", [-1]: "გუშინ", 0: "დღეს", 1: "ხვალ", 2: "ზეგ" },
  },
  week: {
    past: "კვირის წინ",
    future: "კვირაში",
    named: { [-1]: "გასულ კვირაში", 0: "ამ კვირაში", 1: "მომავალ კვირაში" },
  },
  month: { past: "თვის წინ", future: "თვეში", named: { [-1]: "გასულ თვეს", 0: "ამ თვეში", 1: "მომავალ თვეს" } },
  quarter: {
    past: "კვარტალის წინ",
    future: "კვარტალში",
    named: { [-1]: "გასულ კვარტალში", 0: "ამ კვარტალში", 1: "შემდეგ კვარტალში" },
  },
  year: { past: "წლის წინ", future: "წელიწადში", named: { [-1]: "გასულ წელს", 0: "ამ წელს", 1: "მომავალ წელს" } },
};

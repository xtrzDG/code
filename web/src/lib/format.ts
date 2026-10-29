/**
 * Locale-aware formatting with Intl (`lib/intl/formatters`, which writes
 * Georgian itself: Chrome has none). Dates and times are shown in the
 * business time zone, money in the business currency (see
 * components/business/BusinessContext `useBusinessFormat()` for bound helpers).
 *
 * The API sends timestamps as UNIX microseconds and money as integers in
 * minor units (cents, tetri).
 */

import { CURRENCY_MINOR_DIGITS } from "./currencyDigits.generated";
import { dateTimeFormat, numberFormat } from "./intl/formatters";

export type Timestamp = Date | number;

/** UNIX microseconds (API) -> Date. Dates pass through. */
export function toDate(value: Timestamp): Date {
  return value instanceof Date ? value : new Date(Math.floor(value / 1000));
}

/**
 * The zone is required: a format without one takes the zone of whatever
 * runs it (the server's UTC, then the browser's own), so the server and the
 * browser write different text and React's hydration fails (#418).
 */
export function formatDateTime(
  value: Timestamp,
  options: { locale: string; timeZone: string; dateStyle?: "full" | "long" | "medium" | "short"; timeStyle?: "short" | "medium" },
): string {
  return dateTimeFormat(options.locale, {
    dateStyle: options.dateStyle ?? "medium",
    timeStyle: options.timeStyle ?? "short",
    timeZone: options.timeZone,
  }).format(toDate(value));
}

export function formatDate(
  value: Timestamp,
  options: { locale: string; timeZone: string; dateStyle?: "full" | "long" | "medium" | "short" },
): string {
  return dateTimeFormat(options.locale, {
    dateStyle: options.dateStyle ?? "medium",
    timeZone: options.timeZone,
  }).format(toDate(value));
}

export function formatTime(value: Timestamp, options: { locale: string; timeZone: string }): string {
  return dateTimeFormat(options.locale, { timeStyle: "short", timeZone: options.timeZone }).format(
    toDate(value),
  );
}

export function formatNumber(value: number, locale: string, options?: Intl.NumberFormatOptions): string {
  return numberFormat(locale, options).format(value);
}

/**
 * Digits after the decimal point of a currency (GEL 2, JPY 0, KWD 3), as the
 * backend counts minor units. The browser's own Intl data is only a fallback
 * for codes the table lacks: it differs between browser versions.
 */
export function currencyFractionDigits(currency: string): number {
  const known = CURRENCY_MINOR_DIGITS[currency.toUpperCase()];
  if (known !== undefined) {
    return known;
  }
  try {
    return new Intl.NumberFormat("en", { style: "currency", currency }).resolvedOptions().maximumFractionDigits ?? 2;
  } catch {
    return 2;
  }
}

/** 1850 tetri -> 18.5 GEL. */
export function minorToMajor(minor: number, currency: string): number {
  return minor / 10 ** currencyFractionDigits(currency);
}

/** 18.5 GEL -> 1850 tetri (rounded to the currency's precision). */
export function majorToMinor(major: number, currency: string): number {
  return Math.round(major * 10 ** currencyFractionDigits(currency));
}

/** A price in minor units as text: formatMoney(1850, "GEL", "ka") -> "18,50 ₾". */
export function formatMoney(minor: number, currency: string, locale: string): string {
  const digits = currencyFractionDigits(currency);
  return numberFormat(locale, {
    style: "currency",
    currency,
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(minorToMajor(minor, currency));
}

/** Spaces, thin spaces and apostrophes people type as thousands grouping. */
function compactDecimal(text: string): string {
  return text.replace(/[\s  ']/g, "");
}

/** One separator before exactly three digits: "1,200", "25.000" (grouping in most locales). */
const LONE_GROUPING_LIKE = /^[1-9]\d{0,2}[.,]\d{3}$/;

/** A decimal typed by a person as canonical text ("1200.5"), or null. */
function normalizeDecimalInput(text: string, currency: string): string | null {
  const compact = compactDecimal(text);
  if (compact === "") {
    return null;
  }
  const lastComma = compact.lastIndexOf(",");
  const lastDot = compact.lastIndexOf(".");
  let normalized: string;
  if (lastComma >= 0 && lastDot >= 0) {
    // "1.200,50" or "1,200.50": the last separator is the decimal one.
    const [grouping, decimal] = lastComma > lastDot ? [".", ","] : [",", "."];
    normalized = compact.split(grouping).join("").replace(decimal, ".");
  } else {
    const separator = lastComma >= 0 ? "," : ".";
    const count = compact.split(separator).length - 1;
    // Several separators are grouping ("1.200.000"); so is a lone one before
    // three digits for a currency without decimals ("1,200" yen). Otherwise
    // one separator is decimal ("18,5").
    const isGrouping = count > 1 || (LONE_GROUPING_LIKE.test(compact) && currencyFractionDigits(currency) === 0);
    normalized = isGrouping ? compact.split(separator).join("") : compact.replace(separator, ".");
  }
  return /^\d+(\.\d+)?$/.test(normalized) ? normalized : null;
}

/**
 * A price typed by a person ("18,5", "1 200.50", "1,200" yen) as a number in
 * the currency's major unit, or null. Both "," and "." work as the decimal
 * separator; check the text with `moneyInputProblem` first.
 */
export function parseDecimalInput(text: string, currency: string): number | null {
  const normalized = normalizeDecimalInput(text, currency);
  return normalized === null ? null : Number(normalized);
}

export type MoneyInputProblem = "number" | "ambiguous" | "precision";

/**
 * Why a typed price cannot be stored as it is: not a number; a lone
 * separator before three digits ("1,200" dollars, "25.000" rupiah) that may be
 * thousands or decimals, so it is refused rather than stored 1000 times too
 * low; or more decimals than the currency has. Null when it is fine.
 */
export function moneyInputProblem(text: string, currency: string): MoneyInputProblem | null {
  const normalized = normalizeDecimalInput(text, currency);
  if (normalized === null) {
    return "number";
  }
  const digits = currencyFractionDigits(currency);
  if (digits > 0 && digits < 3 && LONE_GROUPING_LIKE.test(compactDecimal(text))) {
    return "ambiguous";
  }
  // Trailing zeros change nothing ("1500.00" yen is 1500).
  const fraction = normalized.includes(".") ? normalized.slice(normalized.indexOf(".") + 1).replace(/0+$/, "") : "";
  return fraction.length > digits ? "precision" : null;
}

/** The message key for a price problem (shared by every price field). */
export const MONEY_INPUT_MESSAGES = {
  number: "validation.number",
  ambiguous: "knowledge.form.priceAmbiguous",
  precision: "knowledge.form.priceTooPrecise",
} as const satisfies Record<MoneyInputProblem, string>;

/** A decimal for an input field: 18.5 -> "18.5" (no grouping). */
export function decimalInputValue(value: number | null | undefined, fractionDigits: number): string {
  if (value === null || value === undefined) {
    return "";
  }
  return Number(value.toFixed(fractionDigits)).toString();
}

/** Minute of the day -> "HH:MM" (1440 -> "24:00"). */
export function formatMinutesOfDay(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return `${String(hours).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}

/** "HH:MM" (or "H:MM") -> minute of the day 0..1439, else null. */
export function parseTimeOfDay(text: string): number | null {
  const match = /^(\d{1,2}):(\d{2})$/.exec(text.trim());
  if (!match) {
    return null;
  }
  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (hours > 23 || minutes > 59) {
    return null;
  }
  return hours * 60 + minutes;
}

/** ISO weekday (1 = Monday) as a name in the locale: weekdayName(1, "ka") -> "ორშაბათი". */
export function weekdayName(weekday: number, locale: string, width: "long" | "short" = "long"): string {
  // 2024-01-01 was a Monday.
  const date = new Date(Date.UTC(2024, 0, weekday));
  return dateTimeFormat(locale, { weekday: width, timeZone: "UTC" }).format(date);
}

// Kept here for their callers; each lives in a module of its own, so a page
// that formats only dates and money does not carry the table of language names.
export { capitalizeFirst } from "./capitalize";
export { languageName } from "./languageNames";

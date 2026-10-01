/**
 * Locale-aware formatting with Intl. Dates and times are shown in the
 * business time zone, money in the business currency (see
 * components/business/BusinessContext `useBusinessFormat()` for bound helpers).
 *
 * The API sends timestamps as UNIX microseconds and money as integers in
 * minor units (cents, tetri).
 */

export type Timestamp = Date | number;

/** UNIX microseconds (API) -> Date. Dates pass through. */
export function toDate(value: Timestamp): Date {
  return value instanceof Date ? value : new Date(Math.floor(value / 1000));
}

export function formatDateTime(
  value: Timestamp,
  options: { locale: string; timeZone?: string; dateStyle?: "full" | "long" | "medium" | "short"; timeStyle?: "short" | "medium" },
): string {
  return new Intl.DateTimeFormat(options.locale, {
    dateStyle: options.dateStyle ?? "medium",
    timeStyle: options.timeStyle ?? "short",
    timeZone: options.timeZone,
  }).format(toDate(value));
}

export function formatDate(
  value: Timestamp,
  options: { locale: string; timeZone?: string; dateStyle?: "full" | "long" | "medium" | "short" },
): string {
  return new Intl.DateTimeFormat(options.locale, {
    dateStyle: options.dateStyle ?? "medium",
    timeZone: options.timeZone,
  }).format(toDate(value));
}

export function formatTime(value: Timestamp, options: { locale: string; timeZone?: string }): string {
  return new Intl.DateTimeFormat(options.locale, { timeStyle: "short", timeZone: options.timeZone }).format(
    toDate(value),
  );
}

export function formatNumber(value: number, locale: string, options?: Intl.NumberFormatOptions): string {
  return new Intl.NumberFormat(locale, options).format(value);
}

/** Digits after the decimal point of a currency (GEL 2, JPY 0, KWD 3). */
export function currencyFractionDigits(currency: string): number {
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
  return new Intl.NumberFormat(locale, { style: "currency", currency }).format(minorToMajor(minor, currency));
}

/**
 * A decimal typed by a person ("18,5", "1 200.50") as a number, or null.
 * Both "," and "." work as the decimal separator.
 */
export function parseDecimalInput(text: string): number | null {
  const compact = text.replace(/[\s  ']/g, "");
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
    // One separator is decimal ("18,5"); several are grouping ("1.200.000").
    normalized = count > 1 ? compact.split(separator).join("") : compact.replace(separator, ".");
  }
  if (!/^\d+(\.\d+)?$/.test(normalized)) {
    return null;
  }
  return Number(normalized);
}

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
  return new Intl.DateTimeFormat(locale, { weekday: width, timeZone: "UTC" }).format(date);
}

/** "русский" -> "Русский" (names used as labels start with a capital). */
export function capitalizeFirst(text: string, locale?: string): string {
  return text.length > 0 ? text.charAt(0).toLocaleUpperCase(locale) + text.slice(1) : text;
}

/** A language tag as a label in the locale: languageName("ka", "ru") -> "Грузинский". */
export function languageName(tag: string, locale: string): string {
  try {
    return capitalizeFirst(new Intl.DisplayNames([locale], { type: "language" }).of(tag) ?? tag, locale);
  } catch {
    return tag;
  }
}

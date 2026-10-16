/**
 * Fixed English formats that read calendar fields of an instant in a time
 * zone ("en-US"/"en-CA" `formatToParts`), never shown as text, and the
 * questions Intl answers about zones. The only place outside the UI-language
 * factories (`formatters.ts`) that may construct `Intl.DateTimeFormat`
 * (ESLint `no-restricted-syntax`).
 */

type FieldLocale = "en-US" | "en-CA";

const fieldFormats = new Map<string, Intl.DateTimeFormat>();

/** A cached fixed-locale formatter for `formatToParts`; throws RangeError for an unknown zone. */
export function calendarFieldFormat(locale: FieldLocale, options: Intl.DateTimeFormatOptions): Intl.DateTimeFormat {
  const key = `${locale}|${JSON.stringify(options)}`;
  let format = fieldFormats.get(key);
  if (!format) {
    format = new Intl.DateTimeFormat(locale, options);
    fieldFormats.set(key, format);
  }
  return format;
}

/** The parts of an instant in a zone as a map: { year: "2026", month: "10", … }. */
export function calendarParts(
  at: Date,
  timeZone: string,
  options: Intl.DateTimeFormatOptions,
  locale: FieldLocale = "en-US",
): Partial<Record<Intl.DateTimeFormatPartTypes, string>> {
  return Object.fromEntries(
    calendarFieldFormat(locale, { ...options, timeZone })
      .formatToParts(at)
      .map((part) => [part.type, part.value]),
  );
}

/** Whether Intl knows an IANA zone name ("Asia/Tbilisi" yes, "Mars/Base" no). */
export function isKnownTimeZone(zone: string): boolean {
  if (zone.length === 0 || zone.length > 64) {
    return false;
  }
  try {
    calendarFieldFormat("en-US", { timeZone: zone });
    return true;
  } catch {
    return false;
  }
}

/** The zone of the device running this code, or null when Intl does not say. */
export function systemTimeZone(): string | null {
  const zone = new Intl.DateTimeFormat().resolvedOptions().timeZone;
  return zone && isKnownTimeZone(zone) ? zone : null;
}

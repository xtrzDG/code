/**
 * What a date or time field needs to know about a locale's calendar
 * habits: 24- or 12-hour clock, the names of AM and PM, the first day of
 * the week and the order of day, month and year in a typed date.
 *
 * Georgian is answered from CLDR here (Chrome's Intl has no Georgian and
 * would answer as American English: a 12-hour clock and Sunday first).
 * Other locales ask the platform's Intl; the first day of the week comes
 * from CLDR's week data by region, so it is the same in every browser and
 * on the server (Intl.Locale's week info is missing in older engines).
 */

import { georgianDateFormat } from "./georgianDates";

export type HourCycle = "h12" | "h23";

/** ISO weekday: 1 = Monday … 7 = Sunday. */
export type IsoWeekday = 1 | 2 | 3 | 4 | 5 | 6 | 7;

export type DateFieldPart = "day" | "month" | "year";

const isGeorgian = (locale: string): boolean => /^ka(?:[-_]|$)/i.test(locale);

/** CLDR weekData firstDay: regions whose week starts on Sunday. */
const SUNDAY_REGIONS = new Set(
  (
    "AG AS BD BR BS BT BW BZ CA CN CO DM DO ET GT GU HK HN ID IL IN JM JP KE KH KR LA MH MM MO MT MX MZ " +
    "NI NP PA PE PH PK PR PT PY SA SG SV TH TT TW UM US VE VI WS YE ZA ZW"
  ).split(" "),
);
/** CLDR weekData firstDay: regions whose week starts on Saturday (Friday: MV). */
const SATURDAY_REGIONS = new Set("AE AF BH DJ DZ EG IQ IR JO KW LY OM QA SD SY".split(" "));

/** The region a bare language most likely means (CLDR likely subtags), for languages whose week does not start on Monday. */
const LIKELY_REGIONS: Record<string, string> = {
  en: "US",
  he: "IL",
  iw: "IL",
  ar: "EG",
  fa: "IR",
  ps: "AF",
  ja: "JP",
  ko: "KR",
  zh: "CN",
  pt: "BR",
  hi: "IN",
  bn: "BD",
  ur: "PK",
  th: "TH",
  id: "ID",
  km: "KH",
  lo: "LA",
  my: "MM",
  ne: "NP",
  am: "ET",
  dv: "MV",
  fil: "PH",
  sw: "KE",
  zu: "ZA",
  mt: "MT",
};

function tagParts(locale: string): { language: string; region: string | null } {
  const parts = locale.replace(/_/g, "-").split("-");
  const language = (parts[0] ?? "").toLowerCase();
  const region = parts.slice(1).find((part) => /^[A-Za-z]{2}$|^\d{3}$/.test(part));
  return { language, region: region ? region.toUpperCase() : null };
}

/** The first day of the week in a locale: firstDayOfWeek("ru") -> 1 (Monday), ("en") -> 7 (Sunday). */
export function firstDayOfWeek(locale: string): IsoWeekday {
  const { language, region } = tagParts(locale);
  const place = region ?? LIKELY_REGIONS[language] ?? null;
  if (place === null) {
    return 1;
  }
  if (place === "MV") {
    return 5;
  }
  return SUNDAY_REGIONS.has(place) ? 7 : SATURDAY_REGIONS.has(place) ? 6 : 1;
}

const cycles = new Map<string, HourCycle>();

/** The clock a locale reads: "h23" (08:00, 20:00) or "h12" (8:00 AM, 8:00 PM). */
export function hourCycle(locale: string): HourCycle {
  if (isGeorgian(locale)) {
    return "h23";
  }
  let cycle = cycles.get(locale);
  if (!cycle) {
    let resolved: string | undefined;
    try {
      resolved = new Intl.DateTimeFormat(locale, { hour: "numeric", timeZone: "UTC" }).resolvedOptions().hourCycle;
    } catch {
      resolved = undefined;
    }
    cycle = resolved === "h11" || resolved === "h12" ? "h12" : "h23";
    cycles.set(locale, cycle);
  }
  return cycle;
}

export interface DayPeriods {
  am: string;
  pm: string;
}

/** The names of the two halves of a 12-hour day: { am: "AM", pm: "PM" } in English. */
export function dayPeriods(locale: string): DayPeriods {
  const name = (hour: number): string => {
    try {
      const parts = new Intl.DateTimeFormat(locale, { hour: "numeric", hourCycle: "h12", timeZone: "UTC" }).formatToParts(
        new Date(Date.UTC(2024, 0, 1, hour)),
      );
      return parts.find((part) => part.type === "dayPeriod")?.value ?? "";
    } catch {
      return "";
    }
  };
  const am = name(9);
  const pm = name(21);
  return am && pm && am !== pm ? { am, pm } : { am: "AM", pm: "PM" };
}

/** The order of day, month and year in a numeric date: ["month", "day", "year"] in English, day first in Russian. */
export function dateFieldOrder(locale: string): DateFieldPart[] {
  if (isGeorgian(locale)) {
    return ["day", "month", "year"];
  }
  try {
    const order = new Intl.DateTimeFormat(locale, { year: "numeric", month: "numeric", day: "numeric", timeZone: "UTC" })
      .formatToParts(new Date(Date.UTC(2024, 10, 22)))
      .map((part) => part.type)
      .filter((type): type is DateFieldPart => type === "day" || type === "month" || type === "year");
    return order.length === 3 ? order : ["day", "month", "year"];
  } catch {
    return ["day", "month", "year"];
  }
}

/**
 * The month names a person may type in a locale, January first: as dates
 * write them ("октября", "окт."), and on their own ("октябрь"). Georgian
 * from CLDR, others from Intl.
 */
export function monthNames(locale: string): { long: string[]; short: string[]; standalone: string[] } {
  const names = (month: "long" | "short", inDate: boolean): string[] => {
    const georgian = isGeorgian(locale) ? georgianDateFormat({ month, timeZone: "UTC" }) : null;
    return Array.from({ length: 12 }, (_, index) => {
      const date = new Date(Date.UTC(2024, index, 15));
      if (georgian) {
        return georgian.format(date);
      }
      try {
        // With a day the name takes the form used in dates ("октября", not "октябрь").
        const options: Intl.DateTimeFormatOptions = inDate ? { month, day: "numeric", timeZone: "UTC" } : { month, timeZone: "UTC" };
        const parts = new Intl.DateTimeFormat(locale, options).formatToParts(date);
        return parts.find((part) => part.type === "month")?.value ?? "";
      } catch {
        return "";
      }
    });
  };
  return { long: names("long", true), short: names("short", true), standalone: names("long", false) };
}

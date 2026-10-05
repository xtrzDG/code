/**
 * Seasonal nightly rates of a room type, as the item editor edits them.
 *
 * A season runs from a month and day to a month and day every year (both
 * included; over New Year when it ends first, "12-20" to "01-10"). Nights
 * outside every season cost the item's price. Seasons may not share a day,
 * so every night has one rate (the API refuses overlaps, at most 24
 * seasons). Rates are typed in major units of the business currency.
 */

import type { MessageKey } from "@/i18n/translate";

import {
  MONEY_INPUT_MESSAGES,
  currencyFractionDigits,
  decimalInputValue,
  majorToMinor,
  minorToMajor,
  moneyInputProblem,
  parseDecimalInput,
} from "../format";
import { dateTimeFormat } from "../intl/formatters";
import type { SeasonalNightlyRate } from "../offers";

export const MAX_SEASONS = 24;
const MAX_SEASON_NAME_LENGTH = 100;
/** Days of each month in a leap year: "02-29" is a day of a season (it counts in leap years). */
const DAYS_IN_MONTH = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31] as const;

/** One season row of the editor; month and day are kept as chosen ("1".."12", "1".."31"). */
export interface SeasonRow {
  key: string;
  name: string;
  startMonth: string;
  startDay: string;
  endMonth: string;
  endDay: string;
  rate: string;
}

export type SeasonRowErrors = Partial<Record<"name" | "dates" | "rate", MessageKey>>;

export type SeasonsResult =
  | { ok: true; rates: SeasonalNightlyRate[] }
  | { ok: false; rows: SeasonRowErrors[]; overlap: [number, number] | null };

let nextKey = 0;
function rowKey(): string {
  nextKey += 1;
  return `season-${nextKey}`;
}

export function daysInMonth(month: number): number {
  return DAYS_IN_MONTH[month - 1] ?? 31;
}

/** A new season: the summer, empty rate. */
export function emptySeasonRow(): SeasonRow {
  return { key: rowKey(), name: "", startMonth: "6", startDay: "1", endMonth: "8", endDay: "31", rate: "" };
}

/**
 * The season "Add a season" adds: the summer first, then the month after
 * the last season ends (so a new season never starts on top of the last).
 */
export function nextSeasonRow(rows: readonly SeasonRow[]): SeasonRow {
  const last = rows.at(-1);
  if (!last) {
    return emptySeasonRow();
  }
  const endMonth = Number(last.endMonth) || 1;
  const endDay = Number(last.endDay) || 1;
  const startsNextMonth = endDay >= daysInMonth(endMonth);
  const month = startsNextMonth ? (endMonth % 12) + 1 : endMonth;
  const day = startsNextMonth ? 1 : endDay + 1;
  return {
    ...emptySeasonRow(),
    startMonth: String(month),
    startDay: String(day),
    endMonth: String(month),
    endDay: String(daysInMonth(month)),
  };
}

function splitDay(day: string): [string, string] {
  const [month = "1", date = "1"] = day.split("-");
  return [String(Number(month)), String(Number(date))];
}

export function seasonRowsFromRates(rates: readonly SeasonalNightlyRate[], currency: string): SeasonRow[] {
  return rates.map((rate) => {
    const [startMonth, startDay] = splitDay(rate.starts_on);
    const [endMonth, endDay] = splitDay(rate.ends_on);
    return {
      key: rowKey(),
      name: rate.name ?? "",
      startMonth,
      startDay,
      endMonth,
      endDay,
      rate: decimalInputValue(minorToMajor(rate.nightly_rate_minor, currency), currencyFractionDigits(currency)),
    };
  });
}

/** "MM-DD", or null for a day the month does not have. */
export function seasonDay(month: string, day: string): string | null {
  const monthNumber = Number(month);
  const dayNumber = Number(day);
  if (!Number.isInteger(monthNumber) || monthNumber < 1 || monthNumber > 12) {
    return null;
  }
  if (!Number.isInteger(dayNumber) || dayNumber < 1 || dayNumber > daysInMonth(monthNumber)) {
    return null;
  }
  return `${String(monthNumber).padStart(2, "0")}-${String(dayNumber).padStart(2, "0")}`;
}

/** Every "MM-DD" of a season, over New Year when it ends first. */
export function seasonDays(startsOn: string, endsOn: string): string[] {
  const year: string[] = [];
  for (let month = 1; month <= 12; month += 1) {
    for (let day = 1; day <= daysInMonth(month); day += 1) {
      year.push(`${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`);
    }
  }
  return startsOn <= endsOn
    ? year.filter((day) => startsOn <= day && day <= endsOn)
    : year.filter((day) => day >= startsOn || day <= endsOn);
}

/** The first two seasons (by index) that share a day, or null. */
export function overlappingSeasons(rates: readonly Pick<SeasonalNightlyRate, "starts_on" | "ends_on">[]): [number, number] | null {
  const taken = new Map<string, number>();
  for (const [index, rate] of rates.entries()) {
    for (const day of seasonDays(rate.starts_on, rate.ends_on)) {
      const first = taken.get(day);
      if (first !== undefined) {
        return [first, index];
      }
      taken.set(day, index);
    }
  }
  return null;
}

/** The rates to save, or the problems of each row (and the first two seasons that overlap). */
export function validateSeasonRows(rows: readonly SeasonRow[], currency: string): SeasonsResult {
  const errors: SeasonRowErrors[] = [];
  const rates: SeasonalNightlyRate[] = [];
  for (const row of rows) {
    const rowErrors: SeasonRowErrors = {};
    const startsOn = seasonDay(row.startMonth, row.startDay);
    const endsOn = seasonDay(row.endMonth, row.endDay);
    if (!startsOn || !endsOn) {
      rowErrors.dates = "knowledge.offer.errors.seasonDate";
    }
    if (row.name.trim().length > MAX_SEASON_NAME_LENGTH) {
      rowErrors.name = "validation.tooLong";
    }
    const rate = parseDecimalInput(row.rate, currency);
    if (row.rate.trim() === "") {
      rowErrors.rate = "validation.required";
    } else {
      const problem = moneyInputProblem(row.rate, currency);
      if (problem || rate === null) {
        rowErrors.rate = MONEY_INPUT_MESSAGES[problem ?? "number"];
      }
    }
    errors.push(rowErrors);
    if (startsOn && endsOn && rate !== null && Object.keys(rowErrors).length === 0) {
      rates.push({
        starts_on: startsOn,
        ends_on: endsOn,
        nightly_rate_minor: majorToMinor(rate, currency),
        name: row.name.trim() || null,
      });
    }
  }
  if (errors.some((rowErrors) => Object.keys(rowErrors).length > 0)) {
    return { ok: false, rows: errors, overlap: null };
  }
  const overlap = overlappingSeasons(rates);
  return overlap ? { ok: false, rows: errors, overlap } : { ok: true, rates };
}

/** Whether two lists of rates say the same (names, days and rates, in order). */
export function sameRates(left: readonly SeasonalNightlyRate[], right: readonly SeasonalNightlyRate[]): boolean {
  const key = (rates: readonly SeasonalNightlyRate[]) =>
    rates.map((rate) => `${rate.starts_on}|${rate.ends_on}|${rate.nightly_rate_minor}|${rate.name ?? ""}`).join(",");
  return key(left) === key(right);
}

/** Month names in the UI language, January first. */
export function monthNames(locale: string): string[] {
  const format = dateTimeFormat(locale, { month: "long", timeZone: "UTC" });
  return Array.from({ length: 12 }, (_, index) => format.format(new Date(Date.UTC(2024, index, 1))));
}

/** "15 Jun – 31 Aug" in the UI language. */
export function seasonLabel(rate: Pick<SeasonalNightlyRate, "starts_on" | "ends_on">, locale: string): string {
  const format = dateTimeFormat(locale, { day: "numeric", month: "short", timeZone: "UTC" });
  const date = (day: string) => {
    const [month, date] = day.split("-").map(Number);
    return format.format(new Date(Date.UTC(2024, (month ?? 1) - 1, date ?? 1)));
  };
  return `${date(rate.starts_on)} – ${date(rate.ends_on)}`;
}

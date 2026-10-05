/**
 * A retention period in days as people say it: 365 → "1 year", 90 → "3
 * months", 14 → "14 days". Used by Settings → Privacy and by the hosted
 * chat's privacy notice, so both name the same periods the same way.
 */

import type { PluralKey, Translator } from "@/i18n/translate";

export type PeriodUnit = "days" | "months" | "years";

const DAYS_PER_YEAR = 365;
const DAYS_PER_MONTH = 30;

/** A period in its plainest unit (whole years, then whole months, else days). */
export function periodParts(days: number): { unit: PeriodUnit; count: number } {
  if (days >= DAYS_PER_YEAR && days % DAYS_PER_YEAR === 0) {
    return { unit: "years", count: days / DAYS_PER_YEAR };
  }
  if (days >= DAYS_PER_MONTH && days < DAYS_PER_YEAR && days % DAYS_PER_MONTH === 0) {
    return { unit: "months", count: days / DAYS_PER_MONTH };
  }
  return { unit: "days", count: days };
}

const PERIOD_UNIT_KEYS: Record<PeriodUnit, PluralKey> = {
  days: "privacyRetention.periods.days",
  months: "privacyRetention.periods.months",
  years: "privacyRetention.periods.years",
};

/** The period in the reader's language ("2 года", "2 წელი"). */
export function periodLabel(tp: Translator["tp"], days: number): string {
  const parts = periodParts(days);
  return tp(PERIOD_UNIT_KEYS[parts.unit], parts.count);
}

/** A short period counted in days, as the DPA counts model records ("30 days"). */
export function daysLabel(tp: Translator["tp"], days: number): string {
  return tp(PERIOD_UNIT_KEYS.days, days);
}

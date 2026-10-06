/**
 * The bookings the assistant won back, as their own lines of the value
 * hero and the reports: those the waitlist filled (a freed place offered
 * and taken) and those a return-visit message brought back, each with its
 * worth at its own prices and the period before. A line shows only when
 * either period has such bookings (a business without the waitlist or the
 * messages sees none).
 */

import type { ValueTotals } from "./valueModel";

export type GrowthOrigin = "waitlist" | "campaign";

export interface GrowthLine {
  origin: GrowthOrigin;
  count: number;
  previousCount: number;
  /** What the bookings are worth at their own prices; null when none had a price. */
  valueMinor: number | null;
}

export const GROWTH_ORIGINS: readonly GrowthOrigin[] = ["waitlist", "campaign"];

/** The growth fields of a period (a report stored before the lines existed has none). */
type GrowthTotals = Partial<
  Pick<ValueTotals, "waitlist_booking_count" | "waitlist_value_minor" | "campaign_booking_count" | "campaign_value_minor">
>;

function countOf(totals: GrowthTotals, origin: GrowthOrigin): number {
  return (origin === "waitlist" ? totals.waitlist_booking_count : totals.campaign_booking_count) ?? 0;
}

function valueOf(totals: GrowthTotals, origin: GrowthOrigin): number | null {
  return (origin === "waitlist" ? totals.waitlist_value_minor : totals.campaign_value_minor) ?? null;
}

export function growthLines(current: GrowthTotals, previous: GrowthTotals): GrowthLine[] {
  return GROWTH_ORIGINS.map((origin) => ({
    origin,
    count: countOf(current, origin),
    previousCount: countOf(previous, origin),
    valueMinor: valueOf(current, origin),
  })).filter((line) => line.count > 0 || line.previousCount > 0);
}

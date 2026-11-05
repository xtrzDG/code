/**
 * The landing page's value calculator: what the requests a business misses
 * after hours are worth, against the price of a plan. Deliberately
 * conservative: only the after-hours share of the missed requests counts
 * (by day a person may still pick up), and only the share that usually
 * books turns into money.
 *
 *   bookings = missed × after-hours share × conversion
 *   money    = bookings × average check
 */

export interface RoiInputs {
  /** Calls and messages a month nobody answers in time. */
  missedPerMonth: number;
  /** Percent of them that arrive outside working hours. */
  afterHoursPercent: number;
  /** What one booking or order brings, in the plan's currency. */
  averageCheck: number;
  /** Percent of answered requests that become a booking. */
  conversionPercent: number;
}

export interface RoiResult {
  /** After-hours requests the assistant would answer. */
  answeredRequests: number;
  /** Bookings those answers bring (may be fractional; shown rounded). */
  bookings: number;
  /** What those bookings are worth a month. */
  monthlyValue: number;
  /** Value against the plan price ("3.4×"), null when the plan is free or the value is none. */
  multiple: number | null;
  /** Bookings a month that pay for the plan, null without a check. */
  breakEvenBookings: number | null;
}

export const ROI_LIMITS = {
  missedPerMonth: { min: 0, max: 100_000 },
  afterHoursPercent: { min: 0, max: 100 },
  averageCheck: { min: 0, max: 10_000_000 },
  conversionPercent: { min: 0, max: 100 },
} as const satisfies Record<keyof RoiInputs, { min: number; max: number }>;

/** Starting values a visitor then makes their own. */
export const ROI_DEFAULTS: Omit<RoiInputs, "averageCheck"> = {
  missedPerMonth: 120,
  afterHoursPercent: 40,
  conversionPercent: 30,
};

/** A number typed by the visitor, kept inside its field's range (NaN and blanks are 0). */
export function clampInput(field: keyof RoiInputs, value: number): number {
  const { min, max } = ROI_LIMITS[field];
  if (!Number.isFinite(value)) {
    return min;
  }
  return Math.min(max, Math.max(min, value));
}

export function computeRoi(inputs: RoiInputs, planMonthlyPrice: number): RoiResult {
  const missed = clampInput("missedPerMonth", inputs.missedPerMonth);
  const afterHours = clampInput("afterHoursPercent", inputs.afterHoursPercent) / 100;
  const conversion = clampInput("conversionPercent", inputs.conversionPercent) / 100;
  const check = clampInput("averageCheck", inputs.averageCheck);

  const answeredRequests = missed * afterHours;
  const bookings = answeredRequests * conversion;
  const monthlyValue = bookings * check;
  return {
    answeredRequests,
    bookings,
    monthlyValue,
    multiple: planMonthlyPrice > 0 && monthlyValue > 0 ? monthlyValue / planMonthlyPrice : null,
    breakEvenBookings: check > 0 && planMonthlyPrice > 0 ? Math.ceil(planMonthlyPrice / check) : null,
  };
}

/**
 * A niche's typical check (in euro) as a starting value in the plan's
 * currency. Where the plans have their own price book (lari), the check is
 * scaled by the same ratio as the plan's two prices, so both sides of the
 * comparison follow one price level; the result is rounded to a round
 * number, since it is only a starting point. Null without a typical check.
 */
export function startingCheck(
  typicalCheckEuro: number | null,
  planPriceEuro: number,
  planPriceLocal: number,
): number | null {
  if (typicalCheckEuro === null || typicalCheckEuro <= 0) {
    return null;
  }
  const ratio = planPriceEuro > 0 && planPriceLocal > 0 ? planPriceLocal / planPriceEuro : 1;
  return roundNicely(typicalCheckEuro * ratio);
}

/** Two significant digits: 7.4 -> 7, 37.2 -> 37, 142 -> 140, 1234 -> 1200. */
export function roundNicely(value: number): number {
  if (value < 10) {
    return Math.max(1, Math.round(value));
  }
  const step = 10 ** (Math.floor(Math.log10(value)) - 1);
  return Math.round(value / step) * step;
}

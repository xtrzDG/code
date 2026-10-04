/**
 * Pure rules of the value views (the dashboard hero, the change chips and
 * the Reports page): changes against the period before, the staff time
 * saved, money in whole units and the periods of stored reports.
 */

import type { Schema } from "@/api/types";
import { addDays, daysBetween, type LocalDateText } from "@/components/insights/dates";
import { currencyFractionDigits } from "@/lib/format";
import { dateTimeFormat, numberFormat } from "@/lib/intl/formatters";

export type ValueModel = Schema<"ValueModel">;
export type ValueTotals = Schema<"ValueTotals">;
/**
 * The numbers of a period the views compare with the period before: the
 * counts and the money estimate (not how the estimate was made).
 */
export type ValueTotalsNumber = Exclude<keyof ValueTotals, "booked_value_minor" | "revenue_source" | "valued_booking_count">;
export type ValueReport = Schema<"ValueReportView">;
export type ValueReportKind = Schema<"ValueReportKind">;
export type DigestPreferences = Schema<"DigestPreferencesView">;

export const REPORT_KINDS = ["monthly", "weekly", "daily"] as const satisfies readonly ValueReportKind[];

export function isReportKind(value: unknown): value is ValueReportKind {
  return typeof value === "string" && (REPORT_KINDS as readonly string[]).includes(value);
}

export type Direction = "up" | "down" | "same";

export interface Change {
  direction: Direction;
  /** The change in whole percent (no sign); null when the period before had none. */
  percent: number | null;
  /** current - previous. */
  difference: number;
}

/** How a number moved since the period before; null when both are zero (nothing to say). */
export function changeOf(current: number, previous: number): Change | null {
  if (current === 0 && previous === 0) {
    return null;
  }
  const difference = current - previous;
  const direction: Direction = difference > 0 ? "up" : difference < 0 ? "down" : "same";
  if (previous === 0) {
    return { direction, percent: null, difference };
  }
  return { direction, percent: Math.round((Math.abs(difference) / previous) * 100), difference };
}

/**
 * Whether a period had no activity at all (no conversation, message,
 * booking, request, handoff or call): changes against it would present the
 * whole total as growth ("+41"), so the chips say "first period" instead.
 */
export function hadNoActivity(totals: Pick<
  ValueTotals,
  "conversation_count" | "customer_message_count" | "booking_count" | "request_count" | "handoff_count" | "call_count"
>): boolean {
  return (
    totals.conversation_count +
      totals.customer_message_count +
      totals.booking_count +
      totals.request_count +
      totals.handoff_count +
      totals.call_count ===
    0
  );
}

/** Which way is good news for a number: more bookings is, more handoffs is neither. */
export type Polarity = "more-is-better" | "neutral";

export type Sentiment = "positive" | "negative" | "neutral";

export function sentimentOf(change: Change, polarity: Polarity): Sentiment {
  if (polarity === "neutral" || change.direction === "same") {
    return "neutral";
  }
  return change.direction === "up" ? "positive" : "negative";
}

/** The arrow and the size of a change: "▲ 12%", "▼ <1%", "▲ +5" (from none), "= 0%". */
export function changeLabel(change: Change, formatNumber: (value: number) => string, formatPercent: (percent: number) => string): string {
  const arrow = change.direction === "up" ? "▲" : change.direction === "down" ? "▼" : "=";
  if (change.percent === null) {
    return `${arrow} +${formatNumber(change.difference)}`;
  }
  if (change.percent === 0 && change.direction !== "same") {
    return `${arrow} <${formatPercent(1)}`;
  }
  return `${arrow} ${formatPercent(change.percent)}`;
}

/** Days in an inclusive range of local dates. */
export function periodDays(from: LocalDateText, to: LocalDateText): number {
  return daysBetween(from, to) + 1;
}

/** Staff time as whole hours from an hour on (rounded), else minutes. */
export function savedTime(minutes: number): { unit: "hours" | "minutes"; count: number } {
  if (minutes >= 60) {
    return { unit: "hours", count: Math.round(minutes / 60) };
  }
  return { unit: "minutes", count: Math.max(0, minutes) };
}

/** An estimate in whole units of the currency: 264000 tetri -> "GEL 2,640" (as the locale writes it). */
export function formatWholeMoney(minor: number, currency: string, locale: string): string {
  const major = Math.round(minor / 10 ** currencyFractionDigits(currency));
  return numberFormat(locale, { style: "currency", currency, minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(major);
}

/** What the estimate counts: the assistant's bookings, or its requests for niches that take orders. */
export function earningCount(basis: Schema<"ValueBasis">, totals: ValueTotals): number {
  return basis === "requests" ? totals.request_count : totals.assistant_booking_count;
}

/** The dates of the month a "YYYY-MM" key names: "2026-09" -> Sep 1 to Sep 30. */
export function monthOfKey(periodKey: string): { year: number; month: number } | null {
  const match = /^(\d{4})-(\d{2})$/.exec(periodKey);
  return match ? { year: Number(match[1]), month: Number(match[2]) } : null;
}

/** "September 2026" in the locale, for a monthly report. */
export function formatMonth(periodKey: string, locale: string): string {
  const month = monthOfKey(periodKey);
  if (!month) {
    return periodKey;
  }
  const date = new Date(Date.UTC(month.year, month.month - 1, 1));
  return dateTimeFormat(locale, { month: "long", year: "numeric", timeZone: "UTC" }).format(date);
}

/** The first day of the month after a local date's month: the next monthly report. */
export function nextMonthStart(today: LocalDateText): LocalDateText {
  const [year, month] = today.split("-").map(Number) as [number, number];
  const next = month === 12 ? `${year + 1}-01-01` : `${year}-${String(month + 1).padStart(2, "0")}-01`;
  return next;
}

/** The days of the month up to today, the period the "this month" card shows. */
export function monthSoFar(today: LocalDateText): { from: LocalDateText; to: LocalDateText } {
  return { from: `${today.slice(0, 8)}01`, to: today };
}

/** The day before a local date (the "today" period compares with it). */
export function dayBefore(date: LocalDateText): LocalDateText {
  return addDays(date, -1);
}

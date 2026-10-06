/** Pure rules of the Reports page: report titles, the rows of a report, delivery states. */

import type { BadgeTone } from "@/components/ui";
import { formatLocalDate, formatLocalDateRange } from "@/components/insights/dates";
import { formatMonth, type Polarity, type ValueReport, type ValueReportKind, type ValueTotals, type ValueTotalsNumber } from "@/components/value/valueModel";
import type { MessageKey } from "@/i18n/translate";
import { businessPath } from "@/lib/navigation";

/** How a row's numbers read: counts, staff minutes or money. */
export type RowKind = "count" | "minutes" | "money";

/** A report's numbers: the counts and estimate, and the worth of the waitlist's and return visits' bookings. */
type ReportField = ValueTotalsNumber | "waitlist_value_minor" | "campaign_value_minor";

export interface ReportRow {
  field: ReportField;
  label: MessageKey;
  kind: RowKind;
  polarity: Polarity;
}

/** The rows of a report's details, the value first. */
export const REPORT_ROWS: readonly ReportRow[] = [
  { field: "assistant_booking_count", label: "reports.rows.assistantBookings", kind: "count", polarity: "more-is-better" },
  { field: "estimated_revenue_minor", label: "reports.rows.estimate", kind: "money", polarity: "more-is-better" },
  { field: "staff_minutes_saved", label: "reports.rows.staffTime", kind: "minutes", polarity: "more-is-better" },
  { field: "after_hours_conversation_count", label: "reports.rows.afterHours", kind: "count", polarity: "more-is-better" },
  { field: "conversation_count", label: "reports.rows.conversations", kind: "count", polarity: "more-is-better" },
  { field: "customer_message_count", label: "reports.rows.customerMessages", kind: "count", polarity: "more-is-better" },
  { field: "assistant_reply_count", label: "reports.rows.assistantReplies", kind: "count", polarity: "more-is-better" },
  { field: "call_count", label: "reports.rows.calls", kind: "count", polarity: "more-is-better" },
  { field: "booking_count", label: "reports.rows.bookings", kind: "count", polarity: "more-is-better" },
  { field: "waitlist_booking_count", label: "growthValue.rows.waitlistBookings", kind: "count", polarity: "more-is-better" },
  { field: "waitlist_value_minor", label: "growthValue.rows.waitlistValue", kind: "money", polarity: "more-is-better" },
  { field: "campaign_booking_count", label: "growthValue.rows.campaignBookings", kind: "count", polarity: "more-is-better" },
  { field: "campaign_value_minor", label: "growthValue.rows.campaignValue", kind: "money", polarity: "more-is-better" },
  { field: "request_count", label: "reports.rows.requests", kind: "count", polarity: "more-is-better" },
  { field: "handoff_count", label: "reports.rows.handoffs", kind: "count", polarity: "neutral" },
];

/** The rows of the waitlist's and the return visits' bookings, by the count that shows them. */
const GROWTH_ROWS: Partial<Record<ReportField, "waitlist_booking_count" | "campaign_booking_count">> = {
  waitlist_booking_count: "waitlist_booking_count",
  waitlist_value_minor: "waitlist_booking_count",
  campaign_booking_count: "campaign_booking_count",
  campaign_value_minor: "campaign_booking_count",
};

function countIn(totals: Partial<ValueTotals>, field: "waitlist_booking_count" | "campaign_booking_count"): number {
  return totals[field] ?? 0;
}

/**
 * The rows with something to show: a money row only with a value in either
 * period, and the waitlist's and return visits' rows only when either
 * period had such bookings (a report stored before them has none).
 */
export function visibleRows(current: ValueTotals, previous: ValueTotals): readonly ReportRow[] {
  return REPORT_ROWS.filter((row) => {
    const growth = GROWTH_ROWS[row.field];
    if (growth && countIn(current, growth) === 0 && countIn(previous, growth) === 0) {
      return false;
    }
    return row.kind !== "money" || current[row.field] != null || previous[row.field] != null;
  });
}

/** A report's name: "September 2026", "Sep 21 – 27, 2026" or "Friday, October 2, 2026". */
export function reportTitle(report: Pick<ValueReport, "kind" | "period_key" | "date_from" | "date_to">, locale: string): string {
  switch (report.kind) {
    case "monthly":
      return formatMonth(report.period_key, locale);
    case "weekly":
      return formatLocalDateRange(report.date_from, report.date_to, locale);
    case "daily":
      return formatLocalDate(report.date_from, locale, { dateStyle: "full" });
  }
}

export const DELIVERY_TONES: Record<ValueReport["delivery"], BadgeTone> = {
  sent: "success",
  no_recipients: "neutral",
  quiet: "neutral",
};

/** The Reports page, optionally opened on one report (the link in a digest). */
export function reportsPath(businessId: string, reportId?: string): string {
  const base = businessPath(businessId, "overview/reports");
  return reportId ? `${base}?report=${encodeURIComponent(reportId)}` : base;
}

/** Staff minutes as "2 h 15 min" parts: whole hours and the minutes left. */
export function splitMinutes(minutes: number): { hours: number; minutes: number } {
  const whole = Math.max(0, Math.round(minutes));
  return { hours: Math.floor(whole / 60), minutes: whole % 60 };
}

export const KIND_LABELS: Record<ValueReportKind, MessageKey> = {
  monthly: "reports.kinds.monthly",
  weekly: "reports.kinds.weekly",
  daily: "reports.kinds.daily",
};

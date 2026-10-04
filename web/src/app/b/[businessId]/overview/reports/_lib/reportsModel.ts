/** Pure rules of the Reports page: report titles, the rows of a report, delivery states. */

import type { BadgeTone } from "@/components/ui";
import { formatLocalDate, formatLocalDateRange } from "@/components/insights/dates";
import { formatMonth, type Polarity, type ValueReport, type ValueReportKind, type ValueTotals, type ValueTotalsNumber } from "@/components/value/valueModel";
import type { MessageKey } from "@/i18n/translate";
import { businessPath } from "@/lib/navigation";

/** How a row's numbers read: counts, staff minutes or money. */
export type RowKind = "count" | "minutes" | "money";

export interface ReportRow {
  field: ValueTotalsNumber;
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
  { field: "request_count", label: "reports.rows.requests", kind: "count", polarity: "more-is-better" },
  { field: "handoff_count", label: "reports.rows.handoffs", kind: "count", polarity: "neutral" },
];

/** The rows with something to show: the money row only with an estimate in either period. */
export function visibleRows(current: ValueTotals, previous: ValueTotals): readonly ReportRow[] {
  return REPORT_ROWS.filter(
    (row) => row.kind !== "money" || current.estimated_revenue_minor != null || previous.estimated_revenue_minor != null,
  );
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

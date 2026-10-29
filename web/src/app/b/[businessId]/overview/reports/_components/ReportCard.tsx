"use client";

import { IconChevronRight } from "@/components/icons";
import { Badge } from "@/components/ui";
import { periodDays, type ValueReport } from "@/components/value/valueModel";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { DELIVERY_TONES, reportTitle } from "../_lib/reportsModel";
import { ReportDetails } from "./ReportDetails";
import { ReportSummary } from "./ReportSummary";

/**
 * One stored report: its period, whether it was sent, the period in one
 * glance and, unfolded, every number against the period before.
 */
export function ReportCard({ report, isOpen = false }: { report: ValueReport; isOpen?: boolean }) {
  const { t, tp, locale } = useI18n();
  const delivery =
    report.delivery === "sent"
      ? tp("reports.delivery.sent", report.recipient_count)
      : t(report.delivery === "quiet" ? "reports.delivery.quiet" : "reports.delivery.noRecipients");

  return (
    <article
      aria-labelledby={`report-${report.id}`}
      className={cn(
        "motion-lift rounded-2xl border bg-surface p-4 sm:p-5",
        isOpen ? "border-accent/40 shadow-[var(--shadow-lift)]" : "border-line",
      )}
    >
      <header className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 id={`report-${report.id}`} className="text-base font-semibold text-ink first-letter:uppercase">
          {reportTitle(report, locale)}
        </h3>
        <Badge tone={DELIVERY_TONES[report.delivery]}>{delivery}</Badge>
      </header>
      <ReportSummary
        current={report.current}
        previous={report.previous}
        basis={report.value_basis}
        currency={report.currency_code}
        days={periodDays(report.date_from, report.date_to)}
      />
      <details open={isOpen} className="group mt-3">
        <summary className="inline-flex cursor-pointer list-none items-center gap-1 rounded-md text-sm font-medium text-accent hover:underline focus-visible:outline-2 focus-visible:outline-focus [&::-webkit-details-marker]:hidden">
          <IconChevronRight className="size-4 transition-transform group-open:rotate-90 rtl:-scale-x-100" aria-hidden />
          {t("reports.details.toggle")}
        </summary>
        <div className="mt-3">
          <ReportDetails report={report} />
        </div>
      </details>
    </article>
  );
}

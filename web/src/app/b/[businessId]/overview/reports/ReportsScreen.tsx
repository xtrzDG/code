"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useCursorPage } from "@/api/useCursorPage";
import { useBusiness } from "@/components/business/BusinessContext";
import { LoadMore } from "@/components/insights/common";
import { SegmentedControl } from "@/components/insights/SegmentedControl";
import { replaceUrlQuery } from "@/components/insights/urlQuery";
import { AnimatedPresenceList } from "@/components/motion";
import { EmptyState, ErrorState, PageHeader, SkeletonCardList } from "@/components/ui";
import { REPORT_KINDS, type ValueReport, type ValueReportKind } from "@/components/value/valueModel";
import { useI18n } from "@/i18n/client";

import { DigestPreferencesCard } from "./_components/DigestPreferencesCard";
import { MonthSoFarCard } from "./_components/MonthSoFarCard";
import { OpenedReport } from "./_components/OpenedReport";
import { ReportCard } from "./_components/ReportCard";
import { KIND_LABELS } from "./_lib/reportsModel";

/** Reports per page; monthly ones cover more than a year. */
const REPORTS_PAGE_SIZE = 12;

/**
 * Overview → Reports (owners): the month so far, the stored monthly
 * reports and weekly and daily digests (the snapshots the summaries were
 * sent from), and which summaries reach the signed-in owner.
 */
export function ReportsScreen({ initialKind, openedReportId }: { initialKind: ValueReportKind | null; openedReportId: string | null }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const [kind, setKind] = useState<ValueReportKind>(initialKind ?? "monthly");
  const reports = useCursorPage<ValueReport, { items?: ValueReport[]; next_cursor?: string | null }>(
    queryKeys.reports.list(business.id, kind),
    ({ cursor, limit }) =>
      api.GET("/v1/businesses/{business_id}/value-reports", {
        params: {
          path: { business_id: business.id },
          query: { kind, limit: String(limit), cursor: cursor ?? undefined },
        },
      }),
    { pageSize: REPORTS_PAGE_SIZE },
  );

  const chooseKind = (value: ValueReportKind) => {
    setKind(value);
    replaceUrlQuery(value === "monthly" ? "" : `kind=${value}`);
  };

  return (
    <>
      <PageHeader title={t("navigation.pages.overviewReports")} description={t("reports.description")} />
      <div className="space-y-6">
        {openedReportId ? <OpenedReport reportId={openedReportId} /> : null}
        <MonthSoFarCard />
        <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <section aria-labelledby="reports-past" className="min-w-0 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 id="reports-past" className="text-sm font-semibold tracking-wide text-ink-muted uppercase">
                {t("reports.past")}
              </h2>
              <SegmentedControl
                label={t("reports.kindLabel")}
                value={kind}
                onChange={chooseKind}
                options={REPORT_KINDS.map((value) => ({ value, label: t(KIND_LABELS[value]) }))}
              />
            </div>
            {reports.error && !reports.items ? (
              <ErrorState error={reports.error} onRetry={reports.reload} className="py-6" />
            ) : !reports.items ? (
              <SkeletonCardList cards={3} />
            ) : reports.items.length === 0 ? (
              <EmptyState title={t("reports.empty.title")} description={t(`reports.empty.${kind}`)} />
            ) : (
              <AnimatedPresenceList
                items={reports.items}
                getKey={(report) => report.id}
                className={reports.isPlaceholder ? "animate-settle space-y-3 opacity-60 transition-opacity" : "animate-settle space-y-3 transition-opacity"}
                renderItem={(report) => <ReportCard report={report} />}
              />
            )}
            <LoadMore hasMore={reports.hasMore} isLoading={reports.isLoadingMore} error={reports.moreError} onMore={reports.loadMore} />
          </section>
          <DigestPreferencesCard />
        </div>
      </div>
    </>
  );
}

"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { ButtonLink, ErrorState, SkeletonCard } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { reportsPath } from "../_lib/reportsModel";
import { ReportCard } from "./ReportCard";

/** The report a digest's link opened (`?report=`), unfolded on top of the page. */
export function OpenedReport({ reportId }: { reportId: string }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const report = useQuery(queryKeys.reports.detail(business.id, reportId), () =>
    api.GET("/v1/businesses/{business_id}/value-reports/{report_id}", {
      params: { path: { business_id: business.id, report_id: reportId } },
    }),
  );

  return (
    <section aria-label={t("reports.opened")} className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-semibold tracking-wide text-ink-muted uppercase">{t("reports.opened")}</p>
        <ButtonLink href={reportsPath(business.id)} variant="ghost" size="sm" scroll={false}>
          {t("common.close")}
        </ButtonLink>
      </div>
      {report.error && !report.data ? (
        <ErrorState error={report.error} onRetry={report.reload} className="py-6" />
      ) : report.data ? (
        <ReportCard report={report.data} isOpen />
      ) : (
        <SkeletonCard lines={4} />
      )}
    </section>
  );
}

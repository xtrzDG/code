"use client";

import { RefreshFailed } from "@/components/insights/common";
import { LiveStatus } from "@/components/shell/LiveStatus";
import { Card, ErrorState, LoadingRegion, PageHeader, Skeleton, SkeletonCard } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { useAdminMetrics } from "../../_lib/useAdminMetrics";
import { CohortGrid } from "./CohortGrid";
import { FunnelCard, TunnelCard } from "./FunnelCard";
import { KpiTiles } from "./KpiTiles";
import { MetricsFilters } from "./MetricsFilters";
import { MarginCard, MrrCard } from "./RevenueCards";
import { SourcesCard, WebVitalsCard } from "./SourcesAndVitals";
import { useMetricsFormat } from "./useMetricsFormat";

/**
 * /admin/metrics: the founder's growth numbers from first-party product
 * events. Filters live in the address; the numbers of the previous filters
 * stay (dimmed) while new ones load.
 */
export function MetricsScreen() {
  const { t } = useI18n();
  const { filters, setFilters, metrics, nicheName } = useAdminMetrics();
  const format = useMetricsFormat();
  const view = metrics.data;

  return (
    <>
      <PageHeader
        title={t("adminMetrics.title")}
        description={t("adminMetrics.description")}
        actions={<LiveStatus updatedAt={metrics.updatedAt} isFetching={metrics.isFetching && view !== undefined} />}
      />

      {metrics.error && !view ? (
        <Card>
          <ErrorState error={metrics.error} onRetry={metrics.reload} />
        </Card>
      ) : !view ? (
        <LoadingRegion label={t("common.loading")}>
          <MetricsSkeleton />
        </LoadingRegion>
      ) : (
        <div className="space-y-6">
          {metrics.error ? <RefreshFailed error={metrics.error} onRetry={metrics.reload} /> : null}
          <MetricsFilters filters={filters} setFilters={setFilters} view={view} nicheName={nicheName} />
          <div
            aria-busy={metrics.isPlaceholder || metrics.isFetching}
            className={cn("space-y-6 transition-opacity", metrics.isPlaceholder && "opacity-60")}
          >
            <KpiTiles view={view} format={format} />
            <div className="grid gap-6 xl:grid-cols-2">
              <FunnelCard steps={view.growth.funnel} format={format} />
              <TunnelCard steps={view.growth.tunnel} format={format} />
            </div>
            <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
              <MrrCard mrr={view.revenue.mrr} format={format} />
              <MarginCard margin={view.revenue.margin} format={format} />
            </div>
            <CohortGrid rows={view.growth.cohorts} format={format} />
            {/* Web Vitals need the width of six columns: side by side only on wide screens. */}
            <div className="grid items-start gap-6 2xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
              <SourcesCard rows={view.growth.sources} format={format} />
              <WebVitalsCard rows={view.web_vitals} format={format} />
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/** The page while its numbers load: filters, tiles and cards. */
export function MetricsSkeleton() {
  return (
    <div aria-hidden className="space-y-6">
      <div className="grid gap-4 rounded-2xl border border-line bg-surface p-5 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="h-9 w-full rounded-lg" />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {Array.from({ length: 8 }, (_, index) => (
          <div key={index} className="rounded-2xl border border-line bg-surface p-4">
            <Skeleton className="h-3.5 w-20" />
            <Skeleton className="mt-2.5 h-7 w-16" />
          </div>
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-2">
        <SkeletonCard lines={6} />
        <SkeletonCard lines={6} />
      </div>
    </div>
  );
}

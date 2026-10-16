"use client";

import { Card, TBody, Td, Th, THead, Tr } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { barPercent, type BusinessGrowthView } from "../../_lib/metrics";
import { ScrollingTable } from "./ScrollingTable";
import type { MetricsFormat } from "./useMetricsFormat";

/**
 * Every business created in the period, an owner's second one included:
 * how many, how many by owners who had one before, and the funnel from
 * creation to paying, one bar per step on the scale of the businesses
 * created (the owner funnel next to it counts people, this one businesses).
 */
export function BusinessFunnelCard({ growth, format }: { growth: BusinessGrowthView; format: MetricsFormat }) {
  const { t, tp } = useI18n();
  const title = t("adminMetrics.businesses.title");
  const max = growth.created;
  return (
    <Card title={title} description={t("adminMetrics.businesses.description")} aria-label={title}>
      <p className="text-sm text-ink">
        <span className="font-semibold tabular-nums">{tp("adminMetrics.businesses.created", growth.created)}</span>
        {growth.by_returning_owners > 0 ? (
          <span className="text-ink-muted"> · {tp("adminMetrics.businesses.returning", growth.by_returning_owners)}</span>
        ) : null}
      </p>
      <ol className="mt-4 space-y-3" aria-label={t("adminMetrics.businesses.chartLabel")}>
        {growth.funnel.map((step, index) => (
          <li key={step.step} className="grid gap-x-4 gap-y-1 sm:grid-cols-[minmax(0,12rem)_minmax(0,1fr)] sm:items-center">
            <span className="text-sm font-medium text-ink">{t(`adminMetrics.funnel.steps.${step.step}`)}</span>
            <div className="min-w-0">
              <div className="h-3 overflow-hidden rounded-full bg-surface-muted" aria-hidden>
                <div className="h-full rounded-full bg-current text-chart-3" style={{ width: `${barPercent(step.businesses, max)}%` }} />
              </div>
              <p className="mt-1 flex flex-wrap gap-x-3 text-xs text-ink-muted">
                <span className="font-medium text-ink tabular-nums">{tp("adminMetrics.businesses.count", step.businesses)}</span>
                {index > 0 ? (
                  <>
                    <span>{t("adminMetrics.businesses.ofCreated", { percent: format.percent(step.share_of_created) })}</span>
                    <span>{t("adminMetrics.funnel.fromPrevious", { percent: format.percent(step.share_of_previous) })}</span>
                  </>
                ) : null}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </Card>
  );
}

/** Each screen of the setup tunnel counted per business: entered, finished, skipped, stopped there. */
export function BusinessTunnelCard({ growth, format }: { growth: BusinessGrowthView; format: MetricsFormat }) {
  const { t } = useI18n();
  const title = t("adminMetrics.businesses.tunnelTitle");
  return (
    <Card title={title} description={t("adminMetrics.businesses.tunnelDescription")} padded={false} aria-label={title}>
      <ScrollingTable caption={title}>
        <THead>
          <Tr>
            <Th>{t("adminMetrics.tunnel.screen")}</Th>
            <Th align="right">{t("adminMetrics.tunnel.entered")}</Th>
            <Th align="right">{t("adminMetrics.tunnel.completed")}</Th>
            <Th align="right">{t("adminMetrics.tunnel.skipped")}</Th>
            <Th align="right">{t("adminMetrics.tunnel.stopped")}</Th>
          </Tr>
        </THead>
        <TBody>
          {growth.tunnel.map((step) => (
            <Tr key={step.step}>
              <Th scope="row" className="font-normal text-ink">
                {t(`adminMetrics.tunnel.steps.${step.step}`)}
              </Th>
              <Td align="right" className="tabular-nums">
                {format.number(step.entered)}
              </Td>
              <Td align="right" className="tabular-nums">
                {format.number(step.completed)}
              </Td>
              <Td align="right" className="tabular-nums">
                {format.number(step.skipped)}
              </Td>
              <Td align="right" className={step.stopped_here > 0 ? "font-semibold text-warning tabular-nums" : "tabular-nums"}>
                {format.number(step.stopped_here)}
              </Td>
            </Tr>
          ))}
        </TBody>
      </ScrollingTable>
    </Card>
  );
}

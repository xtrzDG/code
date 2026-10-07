"use client";

import { Card, TBody, Td, Th, THead, Tr } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { barPercent, type FunnelStepView, type TunnelStepView } from "../../_lib/metrics";
import { ScrollingTable } from "./ScrollingTable";
import type { MetricsFormat } from "./useMetricsFormat";

/**
 * The funnel as one bar per step on a shared scale (the sign-ups), in one
 * colour: the bars only shrink, so the length is the story; every bar
 * carries its count and both shares as text.
 */
export function FunnelCard({ steps, format }: { steps: readonly FunnelStepView[]; format: MetricsFormat }) {
  const { t, tp } = useI18n();
  const max = steps[0]?.owners ?? 0;
  const title = t("adminMetrics.funnel.title");
  return (
    <Card title={title} description={t("adminMetrics.funnel.description")} aria-label={title}>
      <ol className="space-y-3" aria-label={t("adminMetrics.funnel.chartLabel")}>
        {steps.map((step, index) => (
          <li key={step.step} className="grid gap-x-4 gap-y-1 sm:grid-cols-[minmax(0,12rem)_minmax(0,1fr)] sm:items-center">
            <span className="text-sm font-medium text-ink">{t(`adminMetrics.funnel.steps.${step.step}`)}</span>
            <div className="min-w-0">
              <div className="h-3 overflow-hidden rounded-full bg-surface-muted" aria-hidden>
                <div className="h-full rounded-full bg-current text-chart-1" style={{ width: `${barPercent(step.owners, max)}%` }} />
              </div>
              <p className="mt-1 flex flex-wrap gap-x-3 text-xs text-ink-muted">
                <span className="font-medium text-ink tabular-nums">{tp("adminMetrics.funnel.owners", step.owners)}</span>
                {index > 0 ? (
                  <>
                    <span>{t("adminMetrics.funnel.ofSignUps", { percent: format.percent(step.share_of_sign_ups) })}</span>
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

/** Each screen of the setup tunnel: entered, finished, skipped, stopped there. */
export function TunnelCard({ steps, format }: { steps: readonly TunnelStepView[]; format: MetricsFormat }) {
  const { t } = useI18n();
  const title = t("adminMetrics.tunnel.title");
  return (
    <Card title={title} description={t("adminMetrics.tunnel.description")} padded={false} aria-label={title}>
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
          {steps.map((step) => (
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

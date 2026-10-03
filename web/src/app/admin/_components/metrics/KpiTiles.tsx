"use client";

import { useI18n } from "@/i18n/client";

import type { AdminMetricsView } from "../../_lib/metrics";
import type { MetricsFormat } from "./useMetricsFormat";

interface Tile {
  key: string;
  label: string;
  value: string;
  detail: string;
}

/** The numbers a founder reads first, each with the facts behind it. */
export function KpiTiles({ view, format }: { view: AdminMetricsView; format: MetricsFormat }) {
  const { t, tp } = useI18n();
  const { growth, revenue } = view;
  const signUps = growth.funnel.find((step) => step.step === "signed_up");
  const live = growth.funnel.find((step) => step.step === "went_live");
  const { activation, trials } = growth;
  const { mrr, margin } = revenue;

  const tiles: Tile[] = [
    {
      key: "signUps",
      label: t("adminMetrics.kpi.signUps"),
      value: format.number(signUps?.owners ?? 0),
      detail: t("adminMetrics.funnel.steps.signed_up"),
    },
    {
      key: "wentLive",
      label: t("adminMetrics.kpi.wentLive"),
      value: format.number(live?.owners ?? 0),
      detail: t("adminMetrics.kpi.ofSignUps", { percent: format.percent(live?.share_of_sign_ups) }),
    },
    {
      key: "timeToLive",
      label: t("adminMetrics.kpi.timeToLive"),
      value: format.duration(growth.median_time_to_live_seconds),
      detail: t("adminMetrics.kpi.timeToLiveDetail"),
    },
    {
      key: "activation",
      label: t("adminMetrics.kpi.activation"),
      value: format.percent(activation.rate),
      detail: t("adminMetrics.kpi.activationDetail", {
        activated: format.number(activation.activated),
        eligible: format.number(activation.eligible),
        pending: format.number(activation.pending),
      }),
    },
    {
      key: "trialToPaid",
      label: t("adminMetrics.kpi.trialToPaid"),
      value: format.percent(trials.rate),
      detail: t("adminMetrics.kpi.trialDetail", {
        converted: format.number(trials.converted),
        ended: format.number(trials.ended),
        started: format.number(trials.started),
      }),
    },
    {
      key: "mrr",
      label: t("adminMetrics.kpi.mrr"),
      value: format.money(mrr.end),
      detail: t("adminMetrics.kpi.mrrDetail", { change: format.signedMoney(mrr.net_change, mrr.end.currency_code) }),
    },
    {
      key: "arpa",
      label: t("adminMetrics.kpi.arpa"),
      value: format.money(mrr.arpa),
      detail: tp("adminMetrics.kpi.arpaDetail", mrr.paying_accounts),
    },
    {
      key: "margin",
      label: t("adminMetrics.kpi.margin"),
      value: format.percent(margin.gross_margin_percent),
      detail: t("adminMetrics.kpi.marginDetail", {
        revenue: format.money(margin.revenue),
        cost: format.money(margin.provider_cost),
      }),
    },
  ];

  return (
    <section aria-label={t("adminMetrics.kpi.label")}>
      <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {tiles.map((tile) => (
          <div key={tile.key} className="min-w-0 rounded-2xl border border-line bg-surface px-4 py-3">
            <dt className="text-xs font-medium text-ink-muted">{tile.label}</dt>
            <dd className="mt-1 text-2xl font-semibold text-ink tabular-nums">{tile.value}</dd>
            <dd className="mt-1 text-xs text-ink-subtle">{tile.detail}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

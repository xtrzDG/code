"use client";

import { Card, TBody, Td, Th, THead, Tr } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { formatRateDate, formatRateValue } from "../../_lib/clients";
import { movementSign, type MarginView, type MrrView } from "../../_lib/metrics";
import { RATE_SOURCE_LABELS } from "../labels";
import { ScrollingTable } from "./ScrollingTable";
import type { MetricsFormat } from "./useMetricsFormat";

/**
 * MRR as a bridge read top to bottom: the start, each movement with its
 * sign (+ adds, − takes away; the sign carries the meaning, the colour
 * only repeats it) and the accounts behind it, then the end.
 */
export function MrrCard({ mrr, format }: { mrr: MrrView; format: MetricsFormat }) {
  const { t } = useI18n();
  const title = t("adminMetrics.mrr.title");
  const currency = mrr.end.currency_code;
  return (
    <Card title={title} description={t("adminMetrics.mrr.description")} padded={false} aria-label={title}>
      <ScrollingTable caption={title}>
        <THead>
          <Tr>
            <Th>{t("adminMetrics.mrr.movement")}</Th>
            <Th align="right">{t("adminMetrics.mrr.amount")}</Th>
            <Th align="right">{t("adminMetrics.mrr.accounts")}</Th>
          </Tr>
        </THead>
        <TBody>
          <Tr>
            <Th scope="row" className="font-medium text-ink">
              {t("adminMetrics.mrr.start")}
            </Th>
            <Td align="right" className="font-medium tabular-nums">
              {format.money(mrr.start)}
            </Td>
            <Td />
          </Tr>
          {mrr.movements.map((movement) => {
            const sign = movementSign(movement.kind);
            const amount = movement.amount.amount_minor;
            return (
              <Tr key={movement.kind}>
                <Th scope="row" className="pl-8 font-normal text-ink-muted">
                  {t(`adminMetrics.mrr.kinds.${movement.kind}`)}
                </Th>
                <Td
                  align="right"
                  className={cn("tabular-nums", amount === 0 ? "text-ink-subtle" : sign > 0 ? "text-success" : "text-danger")}
                >
                  {format.signedMoney(sign * amount, currency)}
                </Td>
                <Td align="right" className="text-ink-muted tabular-nums">
                  {format.number(movement.accounts)}
                </Td>
              </Tr>
            );
          })}
          <Tr className="border-t-2 border-line-strong">
            <Th scope="row" className="font-semibold text-ink">
              {t("adminMetrics.mrr.end")}
            </Th>
            <Td align="right" className="font-semibold tabular-nums">
              {format.money(mrr.end)}
            </Td>
            <Td align="right" className="text-ink-muted tabular-nums">
              {format.number(mrr.paying_accounts)}
            </Td>
          </Tr>
        </TBody>
      </ScrollingTable>
      <RatesNote mrr={mrr} />
      {mrr.unconverted_currencies.length > 0 ? (
        <p className="border-t border-line px-5 py-3 text-xs text-warning">
          {t("adminMetrics.mrr.unconverted", { currencies: mrr.unconverted_currencies.join(", ") })}
        </p>
      ) : null}
    </Card>
  );
}

/**
 * The rates MRR was converted to euros with, each named truthfully: its
 * source (the National Bank of Georgia, the ECB or the platform's planning
 * rate), its day, and a warning when the daily refresh has not brought a
 * newer one.
 */
function RatesNote({ mrr }: { mrr: MrrView }) {
  const { t, locale } = useI18n();
  const rates = mrr.rates ?? [];
  if (rates.length === 0) {
    return mrr.unconverted_currencies.length === 0 ? (
      <p className="border-t border-line px-5 py-3 text-xs text-ink-subtle">{t("adminMetrics.mrr.noConversion")}</p>
    ) : null;
  }
  const text = rates
    .map((rate) => {
      const sources = (rate.sources ?? []).map((source) => t(RATE_SOURCE_LABELS[source]));
      const date = formatRateDate(rate.rate_date, locale);
      const line = t("adminMetrics.mrr.rate", {
        currency: rate.base_currency_code,
        value: formatRateValue(rate.rate_value, locale),
        source: sources.length > 0 ? sources.join(", ") : rate.source,
        date,
      });
      return rate.is_stale ? `${line}, ${t("adminMetrics.mrr.rateStale", { date })}` : line;
    })
    .join("; ");
  return (
    <p className={cn("border-t border-line px-5 py-3 text-xs", rates.some((rate) => rate.is_stale) ? "text-warning" : "text-ink-subtle")}>
      {t("adminMetrics.mrr.rates", { rates: text })}
    </p>
  );
}

/** Revenue against provider cost of the period, and the margin between them. */
export function MarginCard({ margin, format }: { margin: MarginView; format: MetricsFormat }) {
  const { t, tp } = useI18n();
  const title = t("adminMetrics.margin.title");
  const facts: [string, string][] = [
    [t("adminMetrics.margin.revenue"), format.money(margin.revenue)],
    [t("adminMetrics.margin.cost"), format.money(margin.provider_cost)],
    [t("adminMetrics.margin.percent"), format.percent(margin.gross_margin_percent)],
  ];
  return (
    <Card title={title} description={t("adminMetrics.margin.description")} aria-label={title}>
      <dl className="grid grid-cols-3 gap-3">
        {facts.map(([label, value]) => (
          <div key={label} className="min-w-0">
            <dt className="text-xs text-ink-muted">{label}</dt>
            <dd className="mt-1 text-lg font-semibold text-ink tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-4 text-xs text-ink-subtle">{tp("adminMetrics.margin.accounts", margin.accounts)}</p>
      {margin.accounts_without_rate > 0 ? (
        <p className="mt-1 text-xs text-warning">{tp("adminMetrics.margin.withoutRate", margin.accounts_without_rate)}</p>
      ) : null}
    </Card>
  );
}

"use client";

import { Card, Table, TBody, Td, Th, THead, Tr } from "@/components/ui";
import { Facts } from "@/components/workspace/Facts";
import { formatMicroUsd } from "@/components/workspace/helpers";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/lib/format";

import type { AdminClientSummary } from "../../_lib/clients";
import { useClientFormat } from "../../_lib/useClientFormat";
import { Margin } from "../ClientBits";
import { USAGE_KIND_LABELS } from "../labels";

/** This period's costs (LLM and providers), revenue and margin, with the cost of each usage kind. */
export function CostCard({ summary, timeZone }: { summary: AdminClientSummary; timeZone: string }) {
  const { t, locale } = useI18n();
  const { date, money } = useClientFormat(timeZone);
  return (
    <Card
      title={t("admin.detail.costTitle")}
      description={t("admin.detail.costPeriod", { start: date(summary.cost.period_start), end: date(summary.cost.period_end) })}
    >
      <div className="space-y-6">
        <Facts
          columns={3}
          items={[
            { label: t("admin.detail.llmCost"), value: formatMicroUsd(summary.cost.llm_cost_micro_usd, locale) },
            { label: t("admin.detail.providerCostUsd"), value: formatMicroUsd(summary.cost.provider_cost_micro_usd, locale) },
            summary.cost.provider_cost
              ? {
                  label: t("admin.detail.providerCost", { currency: summary.cost.provider_cost.currency_code }),
                  value: money(summary.cost.provider_cost.amount_minor, summary.cost.provider_cost.currency_code),
                }
              : null,
            summary.cost.planned_monthly_provider_cost
              ? {
                  label: t("admin.detail.plannedCost"),
                  value: money(
                    summary.cost.planned_monthly_provider_cost.amount_minor,
                    summary.cost.planned_monthly_provider_cost.currency_code,
                  ),
                }
              : null,
            {
              label: t("admin.detail.revenue"),
              value: money(summary.cost.revenue.amount_minor, summary.cost.revenue.currency_code),
            },
            { label: t("admin.detail.margin"), value: <Margin cost={summary.cost} /> },
          ]}
        />
        <p className="text-xs text-ink-subtle">
          {summary.cost.exchange_rate
            ? t("admin.detail.rate", {
                rate: `1 ${summary.cost.exchange_rate.base_currency_code} = ${formatNumber(summary.cost.exchange_rate.rate, locale, {
                  maximumFractionDigits: 4,
                })} ${summary.cost.exchange_rate.quote_currency_code}`,
                source: summary.cost.exchange_rate.source,
                date: summary.cost.exchange_rate.rate_date,
              })
            : !summary.cost.margin
              ? t("admin.detail.noRate")
              : null}
        </p>
        <section aria-labelledby="admin-usage-lines" className="space-y-2">
          <h3 id="admin-usage-lines" className="text-sm font-semibold text-ink">
            {t("admin.detail.linesTitle")}
          </h3>
          {(summary.cost.usage_cost_lines ?? []).length === 0 ? (
            <p className="text-sm text-ink-muted">{t("admin.detail.noUsage")}</p>
          ) : (
            <div className="rounded-xl border border-line">
              <Table caption={t("admin.detail.linesTitle")}>
                <THead>
                  <Tr>
                    <Th>{t("admin.detail.kind")}</Th>
                    <Th align="right">{t("admin.detail.quantity")}</Th>
                    <Th align="right">{t("admin.detail.cost")}</Th>
                  </Tr>
                </THead>
                <TBody>
                  {(summary.cost.usage_cost_lines ?? []).map((line) => (
                    <Tr key={line.kind}>
                      <Td>{t(USAGE_KIND_LABELS[line.kind])}</Td>
                      <Td align="right">{formatNumber(line.quantity, locale)}</Td>
                      <Td align="right">{formatMicroUsd(line.cost_micro_usd, locale)}</Td>
                    </Tr>
                  ))}
                </TBody>
              </Table>
            </div>
          )}
        </section>
      </div>
    </Card>
  );
}

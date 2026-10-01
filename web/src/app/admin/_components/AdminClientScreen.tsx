"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { useNiches } from "@/api/catalog";
import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import { IconArrowLeft, IconExternal } from "@/components/icons";
import { Badge, Button, ButtonLink, Card, ErrorState, LoadingBlock, PageHeader, Table, TBody, Td, Th, THead, Tr } from "@/components/ui";
import { ConfirmDialog } from "@/components/workspace/ConfirmDialog";
import { Facts } from "@/components/workspace/Facts";
import { formatMicroUsd, usagePercent } from "@/components/workspace/helpers";
import { UsageMeter } from "@/components/workspace/UsageMeter";
import { useI18n } from "@/i18n/client";
import { countryFlag, countryName } from "@/lib/countries";
import { formatDate, formatDateTime, formatMoney, formatNumber, type Timestamp } from "@/lib/format";
import { ADMIN_PATH, businessPath } from "@/lib/navigation";

import { HealthBadge, IssueChips, Margin } from "./ClientBits";
import {
  BUSINESS_STATUS_LABELS,
  INVOICE_KIND_LABELS,
  INVOICE_STATUS_LABELS,
  OUTCOME_LABELS,
  PAYMENT_STATUS_LABELS,
  PLAN_LABELS,
  SCENARIO_LABELS,
  SUBSCRIPTION_LABELS,
  USAGE_KIND_LABELS,
} from "./labels";

/** /admin/clients/[businessId]: one client's health explained, and an audited way into their cabinet. */
export function AdminClientScreen({ businessId }: { businessId: string }) {
  const { t, locale } = useI18n();
  const router = useRouter();
  const niches = useNiches();
  const [isConfirming, setConfirming] = useState(false);
  const [openError, setOpenError] = useState<ApiError | null>(null);

  const detail = useApiQuery(
    () => api.GET("/v1/admin/clients/{business_id}", { params: { path: { business_id: businessId } } }),
    [businessId],
  );
  const open = useApiMutation(
    () => api.POST("/v1/admin/clients/{business_id}/open", { params: { path: { business_id: businessId } } }),
    { errorToast: false },
  );

  const onOpen = async () => {
    const result = await open.run();
    if (result.ok) {
      router.push(businessPath(result.data.business_id, "dashboard"));
    } else {
      setOpenError(result.error);
    }
  };

  const data = detail.data;
  const summary = data?.summary;
  const timeZone = data?.timezone;
  const date = (value: Timestamp) => formatDate(value, { locale, timeZone });
  const dateTime = (value: Timestamp) => formatDateTime(value, { locale, timeZone });
  const money = (minor: number, currency: string) => formatMoney(minor, currency, locale);
  const nicheName = (key: string) => niches.data?.niches.find((niche) => niche.key === key)?.name ?? key;

  return (
    <>
      <ButtonLink href={ADMIN_PATH} variant="ghost" size="sm" className="mb-4 -ml-3" leadingIcon={<IconArrowLeft className="size-4" aria-hidden />}>
        {t("admin.detail.back")}
      </ButtonLink>

      {detail.error && !data ? (
        <Card>
          <ErrorState error={detail.error} onRetry={detail.reload} />
        </Card>
      ) : !data || !summary ? (
        <Card>
          <LoadingBlock label={t("common.loading")} />
        </Card>
      ) : (
        <>
          <PageHeader
            eyebrow={
              <>
                <span aria-hidden>{countryFlag(summary.country_code)} </span>
                {[countryName(summary.country_code, locale), nicheName(summary.niche_key)].join(" · ")}
              </>
            }
            title={<span dir="auto">{summary.name}</span>}
            actions={
              <Button
                leadingIcon={<IconExternal className="size-4" aria-hidden />}
                onClick={() => {
                  setOpenError(null);
                  setConfirming(true);
                }}
              >
                {t("admin.detail.openCabinet")}
              </Button>
            }
          />

          <div className="space-y-6">
            <Card title={t("admin.detail.issuesTitle")} actions={<HealthBadge status={summary.health_status} />}>
              {(summary.health_issues ?? []).length > 0 ? (
                <IssueChips issues={summary.health_issues ?? []} />
              ) : (
                <p className="text-sm text-ink-muted">{t("admin.detail.noIssues")}</p>
              )}
            </Card>

            <div className="grid gap-6 xl:grid-cols-3">
              <Card title={t("admin.detail.overviewTitle")} className="xl:col-span-2">
                <Facts
                  columns={3}
                  items={[
                    { label: t("admin.detail.facts.status"), value: t(BUSINESS_STATUS_LABELS[summary.business_status]) },
                    {
                      label: t("admin.detail.facts.serviceMode"),
                      value: (
                        <Badge tone={summary.service_mode === "full" ? "success" : "danger"}>
                          {t(summary.service_mode === "full" ? "billing.serviceModes.full" : "billing.serviceModes.leads_only")}
                        </Badge>
                      ),
                    },
                    {
                      label: t("admin.detail.facts.plan"),
                      value: [
                        t(PLAN_LABELS[summary.plan_key]),
                        summary.billing_period
                          ? t(summary.billing_period === "annual" ? "billing.periodNames.annual" : "billing.periodNames.monthly")
                          : null,
                      ]
                        .filter(Boolean)
                        .join(" · "),
                    },
                    {
                      label: t("admin.detail.facts.subscription"),
                      value: summary.subscription_status ? t(SUBSCRIPTION_LABELS[summary.subscription_status]) : t("admin.noSubscription"),
                    },
                    summary.period_end ? { label: t("admin.detail.facts.periodEnd"), value: date(summary.period_end) } : null,
                    summary.grace_until ? { label: t("admin.detail.facts.graceUntil"), value: date(summary.grace_until) } : null,
                    {
                      label: t("admin.detail.facts.autoDebit"),
                      value: summary.has_auto_debit ? t("billing.facts.autoDebitOn") : t("common.no"),
                    },
                    {
                      label: t("admin.detail.facts.published"),
                      value:
                        summary.published_version_number !== null && summary.published_version_number !== undefined
                          ? t("admin.detail.facts.publishedValue", {
                              number: summary.published_version_number,
                              date: summary.published_at ? dateTime(summary.published_at) : "",
                            })
                          : t("admin.detail.facts.notPublished"),
                    },
                    {
                      label: t("admin.detail.facts.testScore"),
                      value:
                        summary.last_test_score !== null && summary.last_test_score !== undefined
                          ? `${formatNumber(summary.last_test_score, locale, { maximumFractionDigits: 1 })} / 5`
                          : t("admin.unknown"),
                    },
                    { label: t("admin.detail.facts.failedTests"), value: formatNumber(summary.failed_tests, locale) },
                    { label: t("admin.detail.facts.handoffs"), value: formatNumber(summary.handoffs_last_7_days, locale) },
                    { label: t("admin.detail.facts.toolErrors"), value: formatNumber(summary.tool_errors_last_7_days, locale) },
                    { label: t("admin.detail.facts.openQuestions"), value: formatNumber(summary.open_unanswered_questions, locale) },
                    { label: t("admin.detail.facts.timezone"), value: data.timezone },
                  ]}
                />
              </Card>

              <Card title={t("admin.detail.usageTitle")}>
                <div className="space-y-5">
                  {summary.included_voice_minutes > 0 || summary.used_voice_minutes > 0 ? (
                    <UsageMeter
                      label={t("billing.usage.voice")}
                      usedText={t("billing.usage.minutesOf", {
                        used: formatNumber(summary.used_voice_minutes, locale),
                        included: formatNumber(summary.included_voice_minutes, locale),
                      })}
                      percent={usagePercent(summary.used_voice_minutes, summary.included_voice_minutes)}
                    />
                  ) : null}
                  <UsageMeter
                    label={t("billing.usage.dialogs")}
                    usedText={t("billing.usage.dialogsOf", {
                      used: formatNumber(summary.used_dialogs, locale),
                      included: formatNumber(summary.included_dialogs, locale),
                    })}
                    percent={usagePercent(summary.used_dialogs, summary.included_dialogs)}
                  />
                </div>
              </Card>
            </div>

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

            <Card title={t("admin.detail.autotestsTitle")} padded={(data.failed_autotests ?? []).length === 0}>
              {(data.failed_autotests ?? []).length === 0 ? (
                <p className="text-sm text-ink-muted">{t("admin.detail.noFailedTests")}</p>
              ) : (
                <ul className="divide-y divide-line">
                  {(data.failed_autotests ?? []).map((test) => (
                    <li key={`${test.scenario_key}-${test.language}`} className="space-y-1.5 px-5 py-4 sm:px-6">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-medium text-ink">{t(SCENARIO_LABELS[test.kind])}</span>
                        <Badge tone={test.outcome === "errored" ? "warning" : "danger"}>{t(OUTCOME_LABELS[test.outcome])}</Badge>
                        <Badge>{test.language}</Badge>
                        <code className="text-xs text-ink-subtle">{test.scenario_key}</code>
                      </div>
                      {(test.judge_notes ?? []).length > 0 ? (
                        <ul className="list-disc space-y-0.5 pl-5 text-sm text-ink-muted">
                          {(test.judge_notes ?? []).map((note, index) => (
                            <li key={index} dir="auto">
                              {note}
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <div className="grid gap-6 xl:grid-cols-2">
              <Card title={t("admin.detail.invoicesTitle")} padded={(data.invoices ?? []).length === 0}>
                {(data.invoices ?? []).length === 0 ? (
                  <p className="text-sm text-ink-muted">{t("admin.detail.noInvoices")}</p>
                ) : (
                  <ul className="divide-y divide-line">
                    {(data.invoices ?? []).map((invoice) => (
                      <li key={invoice.id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 sm:px-6">
                        <div className="text-sm">
                          <p className="font-medium text-ink">{t(INVOICE_KIND_LABELS[invoice.kind])}</p>
                          <p className="text-xs text-ink-muted">
                            {t("billing.dateRange", { start: date(invoice.period_start), end: date(invoice.period_end) })}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 text-sm">
                          <span className="font-medium">{money(invoice.amount.amount_minor, invoice.amount.currency_code)}</span>
                          <Badge tone={invoice.status === "paid" ? "success" : invoice.status === "void" ? "neutral" : invoice.status === "failed" ? "danger" : "warning"}>
                            {t(INVOICE_STATUS_LABELS[invoice.status])}
                          </Badge>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
              <Card title={t("admin.detail.paymentsTitle")} padded={(data.payments ?? []).length === 0}>
                {(data.payments ?? []).length === 0 ? (
                  <p className="text-sm text-ink-muted">{t("admin.detail.noPayments")}</p>
                ) : (
                  <ul className="divide-y divide-line">
                    {(data.payments ?? []).map((payment) => (
                      <li key={payment.id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 sm:px-6">
                        <div className="text-sm">
                          <p className="font-medium text-ink">{dateTime(payment.created_at)}</p>
                          {payment.failure_reason ? (
                            <p className="text-xs text-danger" dir="auto">
                              {payment.failure_reason}
                            </p>
                          ) : null}
                        </div>
                        <div className="flex items-center gap-2 text-sm">
                          <span className="font-medium">{money(payment.amount.amount_minor, payment.amount.currency_code)}</span>
                          <Badge
                            tone={
                              payment.status === "approved"
                                ? "success"
                                : payment.status === "declined"
                                  ? "danger"
                                  : payment.status === "processing" || payment.status === "created"
                                    ? "info"
                                    : "neutral"
                            }
                          >
                            {t(PAYMENT_STATUS_LABELS[payment.status])}
                          </Badge>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </div>
          </div>

          <ConfirmDialog
            open={isConfirming}
            onClose={() => setConfirming(false)}
            onConfirm={onOpen}
            tone="primary"
            isPending={open.isPending}
            error={openError}
            title={t("admin.detail.openTitle", { name: summary.name })}
            description={t("admin.detail.openDescription")}
            confirmLabel={t("admin.detail.openCabinet")}
          />
        </>
      )}
    </>
  );
}

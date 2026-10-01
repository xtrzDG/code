"use client";

import Link from "next/link";
import { useState } from "react";

import { useNiches } from "@/api/catalog";
import { api } from "@/api/client";
import { useApiQuery } from "@/api/hooks";
import { IconChevronRight, IconShield } from "@/components/icons";
import { Badge, Button, Card, EmptyState, ErrorState, Field, Input, LoadingBlock, PageHeader, Select, Table, TBody, Td, Th, THead, Tr } from "@/components/ui";
import { usageLevel } from "@/components/workspace/helpers";
import { IconRefresh, IconSearch } from "@/components/workspace/icons";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { countryFlag, countryName } from "@/lib/countries";
import { formatDateTime, formatMoney, formatNumber } from "@/lib/format";

import {
  CLIENT_SORTS,
  EMPTY_FILTERS,
  adminClientPath,
  clientUsagePercent,
  filterClients,
  hasFilters,
  sortClients,
  summarizeClients,
  type AdminClientSummary,
  type BusinessStatus,
  type ClientFilters,
  type ClientHealthStatus,
  type ClientSort,
} from "../_lib/clients";
import { HealthBadge, IssueChips, Margin, ProviderCost } from "./ClientBits";
import { BUSINESS_STATUS_LABELS, HEALTH_LABELS, PLAN_LABELS, SORT_LABELS, SUBSCRIPTION_LABELS } from "./labels";

const HEALTH_VALUES: readonly ClientHealthStatus[] = ["critical", "attention", "healthy"];
const STATUS_VALUES: readonly BusinessStatus[] = ["onboarding", "testing", "live", "paused"];

/** /admin: every client with health, package use, cost and margin; filters and sorting. */
export function AdminClientsScreen() {
  const { t, tp, locale } = useI18n();
  const niches = useNiches();
  const [filters, setFilters] = useState<ClientFilters>(EMPTY_FILTERS);
  const [sort, setSort] = useState<ClientSort>("health");
  const list = useApiQuery(() => api.GET("/v1/admin/clients"), []);

  const nicheName = (key: string) => niches.data?.niches.find((niche) => niche.key === key)?.name ?? key;
  const data = list.data;
  const clients = data ? sortClients(filterClients(data.clients, filters), sort, locale) : [];
  const summary = data ? summarizeClients(data.clients) : null;

  const tiles: { label: string; value: number; health?: ClientHealthStatus; tone: string }[] = summary
    ? [
        { label: t("admin.summary.clients"), value: summary.total, tone: "text-ink" },
        { label: t("admin.summary.critical"), value: summary.critical, health: "critical", tone: "text-danger" },
        { label: t("admin.summary.attention"), value: summary.attention, health: "attention", tone: "text-warning" },
        { label: t("admin.summary.healthy"), value: summary.healthy, health: "healthy", tone: "text-success" },
        { label: t("admin.summary.losingMoney"), value: summary.losingMoney, tone: summary.losingMoney > 0 ? "text-danger" : "text-ink" },
      ]
    : [];

  return (
    <>
      <PageHeader
        title={t("pages.admin.title")}
        description={t("pages.admin.description")}
        actions={
          <>
            {data ? (
              <span className="text-xs text-ink-subtle">
                {t("admin.generatedAt", { time: formatDateTime(data.generated_at, { locale, timeStyle: "short" }) })}
              </span>
            ) : null}
            <Button
              variant="secondary"
              size="sm"
              onClick={list.reload}
              disabled={list.isLoading}
              leadingIcon={<IconRefresh className="size-4" aria-hidden />}
            >
              {t("workspace.refresh")}
            </Button>
          </>
        }
      />

      {list.error && !data ? (
        <Card>
          <ErrorState error={list.error} onRetry={list.reload} />
        </Card>
      ) : !data ? (
        <Card>
          <LoadingBlock label={t("common.loading")} />
        </Card>
      ) : (
        <div className="space-y-6">
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {tiles.map((tile) => {
              const content = (
                <>
                  <span className="text-xs font-medium text-ink-muted">{tile.label}</span>
                  <span className={cn("mt-1 block text-2xl font-semibold", tile.tone)}>{formatNumber(tile.value, locale)}</span>
                </>
              );
              const isActive = tile.health !== undefined && filters.health === tile.health;
              return (
                <li key={tile.label}>
                  {tile.health ? (
                    <button
                      type="button"
                      aria-pressed={isActive}
                      onClick={() => setFilters((current) => ({ ...current, health: isActive ? "" : (tile.health ?? "") }))}
                      className={cn(
                        "block w-full rounded-2xl border bg-surface px-4 py-3 text-left shadow-sm transition-colors hover:border-accent/40",
                        isActive ? "border-accent-solid ring-1 ring-accent-solid" : "border-line",
                      )}
                    >
                      {content}
                    </button>
                  ) : (
                    <div className="rounded-2xl border border-line bg-surface px-4 py-3 shadow-sm">{content}</div>
                  )}
                </li>
              );
            })}
          </ul>

          <Card padded={false}>
            <div role="search" aria-label={t("admin.filtersLabel")} className="grid gap-4 border-b border-line px-5 py-4 sm:grid-cols-2 sm:px-6 lg:grid-cols-4">
              <Field label={t("admin.search")}>
                {(control) => (
                  <div className="relative">
                    <IconSearch className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-subtle" aria-hidden />
                    <Input
                      {...control}
                      type="search"
                      dir="auto"
                      className="pl-9"
                      value={filters.query}
                      placeholder={t("admin.searchPlaceholder")}
                      onChange={(event) => setFilters((current) => ({ ...current, query: event.target.value }))}
                    />
                  </div>
                )}
              </Field>
              <Field label={t("admin.healthFilter")}>
                {(control) => (
                  <Select
                    {...control}
                    value={filters.health}
                    onChange={(event) => setFilters((current) => ({ ...current, health: event.target.value as ClientHealthStatus | "" }))}
                  >
                    <option value="">{t("admin.all")}</option>
                    {HEALTH_VALUES.map((value) => (
                      <option key={value} value={value}>
                        {t(HEALTH_LABELS[value])}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
              <Field label={t("admin.statusFilter")}>
                {(control) => (
                  <Select
                    {...control}
                    value={filters.status}
                    onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value as BusinessStatus | "" }))}
                  >
                    <option value="">{t("admin.all")}</option>
                    {STATUS_VALUES.map((value) => (
                      <option key={value} value={value}>
                        {t(BUSINESS_STATUS_LABELS[value])}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
              <Field label={t("admin.sort")}>
                {(control) => (
                  <Select {...control} value={sort} onChange={(event) => setSort(event.target.value as ClientSort)}>
                    {CLIENT_SORTS.map((value) => (
                      <option key={value} value={value}>
                        {t(SORT_LABELS[value])}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 text-sm text-ink-muted sm:px-6" aria-live="polite">
              <span>{tp("admin.count", clients.length)}</span>
              {hasFilters(filters) ? (
                <Button variant="ghost" size="sm" onClick={() => setFilters(EMPTY_FILTERS)}>
                  {t("admin.clearFilters")}
                </Button>
              ) : null}
            </div>

            {data.clients.length === 0 ? (
              <EmptyState icon={<IconShield className="size-6" />} title={t("admin.emptyTitle")} description={t("admin.emptyDescription")} />
            ) : clients.length === 0 ? (
              <EmptyState icon={<IconSearch className="size-6" />} title={t("admin.emptyFiltered")} />
            ) : (
              <>
                <div className="hidden border-t border-line lg:block">
                  <Table caption={t("pages.admin.title")}>
                    <THead>
                      <Tr>
                        <Th>{t("admin.columns.client")}</Th>
                        <Th>{t("admin.columns.health")}</Th>
                        <Th>{t("admin.columns.plan")}</Th>
                        <Th>{t("admin.columns.usage")}</Th>
                        <Th align="right">{t("admin.columns.cost")}</Th>
                        <Th align="right">{t("admin.columns.revenue")}</Th>
                        <Th align="right">{t("admin.columns.margin")}</Th>
                      </Tr>
                    </THead>
                    <TBody>
                      {clients.map((client) => (
                        <Tr key={client.business_id}>
                          <Td>
                            <Link href={adminClientPath(client.business_id)} className="font-medium text-ink hover:text-accent hover:underline" dir="auto">
                              {client.name}
                            </Link>
                            <p className="mt-0.5 text-xs text-ink-muted">
                              <span aria-hidden>{countryFlag(client.country_code)} </span>
                              {[countryName(client.country_code, locale), nicheName(client.niche_key)].join(" · ")}
                            </p>
                            <p className="mt-1 text-xs text-ink-subtle">{t(BUSINESS_STATUS_LABELS[client.business_status])}</p>
                          </Td>
                          <Td className="max-w-64">
                            <div className="space-y-1.5">
                              <HealthBadge status={client.health_status} />
                              <IssueChips issues={client.health_issues ?? []} limit={3} />
                            </div>
                          </Td>
                          <Td>
                            <p>{t(PLAN_LABELS[client.plan_key])}</p>
                            <p className="mt-0.5 text-xs text-ink-muted">
                              {client.subscription_status ? t(SUBSCRIPTION_LABELS[client.subscription_status]) : t("admin.noSubscription")}
                            </p>
                          </Td>
                          <Td>
                            <UsageSummary client={client} />
                          </Td>
                          <Td align="right" className="whitespace-nowrap">
                            <ProviderCost cost={client.cost} />
                          </Td>
                          <Td align="right" className="whitespace-nowrap">
                            {formatMoney(client.cost.revenue.amount_minor, client.cost.revenue.currency_code, locale)}
                          </Td>
                          <Td align="right" className="whitespace-nowrap">
                            <Margin cost={client.cost} />
                          </Td>
                        </Tr>
                      ))}
                    </TBody>
                  </Table>
                </div>
                <ul className="divide-y divide-line border-t border-line lg:hidden">
                  {clients.map((client) => (
                    <li key={client.business_id}>
                      <Link
                        href={adminClientPath(client.business_id)}
                        className="flex items-start gap-3 px-5 py-4 hover:bg-surface-muted/60 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus sm:px-6"
                        aria-label={t("admin.openDetails", { name: client.name })}
                      >
                        <div className="min-w-0 flex-1 space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-medium text-ink" dir="auto">
                              {client.name}
                            </span>
                            <HealthBadge status={client.health_status} />
                          </div>
                          <p className="text-xs text-ink-muted">
                            <span aria-hidden>{countryFlag(client.country_code)} </span>
                            {[
                              nicheName(client.niche_key),
                              t(PLAN_LABELS[client.plan_key]),
                              client.subscription_status ? t(SUBSCRIPTION_LABELS[client.subscription_status]) : t("admin.noSubscription"),
                            ].join(" · ")}
                          </p>
                          <IssueChips issues={client.health_issues ?? []} limit={3} />
                          <UsageSummary client={client} />
                          <dl className="grid grid-cols-3 gap-2 text-xs">
                            <div>
                              <dt className="text-ink-subtle">{t("admin.columns.cost")}</dt>
                              <dd className="font-medium">
                                <ProviderCost cost={client.cost} />
                              </dd>
                            </div>
                            <div>
                              <dt className="text-ink-subtle">{t("admin.columns.revenue")}</dt>
                              <dd className="font-medium">
                                {formatMoney(client.cost.revenue.amount_minor, client.cost.revenue.currency_code, locale)}
                              </dd>
                            </div>
                            <div>
                              <dt className="text-ink-subtle">{t("admin.columns.margin")}</dt>
                              <dd className="font-medium">
                                <Margin cost={client.cost} />
                              </dd>
                            </div>
                          </dl>
                        </div>
                        <IconChevronRight className="mt-1 size-5 shrink-0 text-ink-subtle" aria-hidden />
                      </Link>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </Card>
        </div>
      )}
    </>
  );
}

function UsageSummary({ client }: { client: AdminClientSummary }) {
  const { t, locale } = useI18n();
  const percent = clientUsagePercent(client);
  const level = usageLevel(percent);
  return (
    <div className="space-y-1 text-xs text-ink-muted">
      {client.included_voice_minutes > 0 ? (
        <p>
          {t("admin.minutesShort", {
            used: formatNumber(client.used_voice_minutes, locale),
            included: formatNumber(client.included_voice_minutes, locale),
          })}
        </p>
      ) : null}
      <p>
        {t("admin.dialogsShort", {
          used: formatNumber(client.used_dialogs, locale),
          included: formatNumber(client.included_dialogs, locale),
        })}
      </p>
      {level === "warning" || level === "exceeded" ? (
        <Badge tone={level === "exceeded" ? "danger" : "warning"}>
          {new Intl.NumberFormat(locale, { style: "percent" }).format((percent ?? 0) / 100)}
        </Badge>
      ) : null}
    </div>
  );
}

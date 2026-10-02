"use client";

import { IconRefresh, IconSearch, IconShield } from "@/components/icons";
import { RefreshFailed } from "@/components/insights/common";
import { Button, Card, EmptyState, ErrorState, LoadingBlock, PageHeader } from "@/components/ui";
import { InlineError } from "@/components/ui/InlineError";
import { useI18n } from "@/i18n/client";
import { formatDateTime } from "@/lib/format";

import { EMPTY_FILTERS, hasFilters } from "../_lib/clients";
import { useAdminClients } from "../_lib/useAdminClients";
import { ClientCards } from "./clients/ClientCards";
import { ClientFiltersBar } from "./clients/ClientFiltersBar";
import { ClientsTable } from "./clients/ClientsTable";
import { SummaryTiles } from "./clients/SummaryTiles";

/**
 * /admin: clients with health, package use, cost and margin. Filters,
 * sorting and paging run on the server; the tiles count every client.
 */
export function AdminClientsScreen() {
  const { t, tp, locale } = useI18n();
  const { filters, setFilters, sort, setSort, list, nicheName } = useAdminClients();
  const data = list.firstPage;
  const clients = list.items;
  const totals = data?.totals;

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
      ) : !data || !totals ? (
        <Card>
          <LoadingBlock label={t("common.loading")} />
        </Card>
      ) : (
        <div className="space-y-6">
          {list.error ? <RefreshFailed error={list.error} onRetry={list.reload} /> : null}
          <SummaryTiles totals={totals} filters={filters} setFilters={setFilters} />

          <Card padded={false}>
            <ClientFiltersBar data={data} filters={filters} setFilters={setFilters} sort={sort} setSort={setSort} nicheName={nicheName} />

            <div className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 text-sm text-ink-muted sm:px-6" aria-live="polite">
              {/* After a failed reload the count belongs to the earlier filters. */}
              <span>{list.error ? null : tp("admin.count", data.matching_count)}</span>
              {hasFilters(filters) ? (
                <Button variant="ghost" size="sm" onClick={() => setFilters(EMPTY_FILTERS)}>
                  {t("admin.clearFilters")}
                </Button>
              ) : null}
            </div>

            {totals.client_count === 0 ? (
              <EmptyState icon={<IconShield className="size-6" />} title={t("admin.emptyTitle")} description={t("admin.emptyDescription")} />
            ) : clients.length === 0 ? (
              list.error ? null : list.isLoading ? (
                <LoadingBlock label={t("common.loading")} />
              ) : (
                <EmptyState icon={<IconSearch className="size-6" />} title={t("admin.emptyFiltered")} />
              )
            ) : (
              <div aria-busy={list.isLoading}>
                <ClientsTable clients={clients} nicheName={nicheName} />
                <ClientCards clients={clients} nicheName={nicheName} />
                {list.hasMore || list.moreError ? (
                  <div className="space-y-2 border-t border-line px-5 py-3 sm:px-6">
                    <InlineError error={list.moreError} />
                    {list.hasMore ? (
                      <Button variant="secondary" size="sm" isLoading={list.isLoadingMore} onClick={list.loadMore}>
                        {t("workspace.loadMore")}
                      </Button>
                    ) : null}
                  </div>
                ) : null}
              </div>
            )}
          </Card>
        </div>
      )}
    </>
  );
}

"use client";

import { IconSearch, IconShield } from "@/components/icons";
import { RefreshFailed } from "@/components/insights/common";
import { Button, Card, EmptyState, ErrorState, InlineError, LoadingRegion, PageHeader, SkeletonRows } from "@/components/ui";
import { LiveStatus } from "@/components/shell/LiveStatus";
import { useI18n } from "@/i18n/client";

import { EMPTY_FILTERS, hasFilters } from "../_lib/clients";
import { useAdminClients } from "../_lib/useAdminClients";
import { AdminClientsSkeleton } from "./AdminSkeletons";
import { ClientCards } from "./clients/ClientCards";
import { ClientFiltersBar } from "./clients/ClientFiltersBar";
import { ClientsTable } from "./clients/ClientsTable";
import { SummaryTiles } from "./clients/SummaryTiles";

/**
 * /admin: clients with health, package use, cost and margin. Filters,
 * sorting and paging run on the server; the tiles count every client.
 */
export function AdminClientsScreen() {
  const { t, tp } = useI18n();
  const { filters, setFilters, sort, setSort, list, nicheName } = useAdminClients();
  const data = list.page;
  const clients = list.items ?? [];
  const totals = data?.totals;

  return (
    <>
      <PageHeader
        title={t("pages.admin.title")}
        description={t("pages.admin.description")}
        status={<LiveStatus updatedAt={list.updatedAt} isFetching={list.isFetching && data !== undefined} />}
      />

      {list.error && !data ? (
        <Card>
          <ErrorState error={list.error} onRetry={list.reload} />
        </Card>
      ) : !data || !totals ? (
        <LoadingRegion label={t("common.loading")}>
          <AdminClientsSkeleton />
        </LoadingRegion>
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
              list.error ? null : list.isLoading || list.isPlaceholder ? (
                <LoadingRegion label={t("common.loading")} className="px-5 pb-5 sm:px-6">
                  <SkeletonRows rows={4} />
                </LoadingRegion>
              ) : (
                <EmptyState icon={<IconSearch className="size-6" />} title={t("admin.emptyFiltered")} />
              )
            ) : (
              <div aria-busy={list.isPlaceholder || list.isFetching}>
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

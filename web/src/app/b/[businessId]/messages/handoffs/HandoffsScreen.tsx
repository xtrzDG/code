"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useCursorPage } from "@/api/useCursorPage";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconCheck, IconHandoff } from "@/components/icons";
import { IncludeTestToggle, LoadMore, RefreshButton, RefreshFailed } from "@/components/insights/common";
import { SegmentedControl } from "@/components/insights/SegmentedControl";
import type { HandoffListItem, HandoffPage } from "@/components/insights/types";
import { useAutoReload } from "@/components/insights/useAutoReload";
import { replaceUrlQuery } from "@/components/insights/urlQuery";
import {
  Card,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  LoadingRegion,
  PageHeader,
  SkeletonCardList,
} from "@/components/ui";
import { AnimatedPresenceList } from "@/components/motion";
import { useI18n } from "@/i18n/client";

import { HandoffCard } from "./_components/HandoffCard";
import { HANDOFF_TABS, handoffFiltersQuery, handoffTabCounts, isOpenQuery, type HandoffFilters } from "./_components/handoffModel";
import { useResolveHandoff } from "./_components/useResolveHandoff";

/**
 * Handoffs (concept /handoffs): conversations the assistant passed to a
 * person, the most urgent open ones first, with the summary, the customer
 * to call back and "resolve" (the assistant answers the customer again).
 */
export function HandoffsScreen({ initialFilters }: { initialFilters: HandoffFilters }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const businessId = business.id;
  const [filters, setFiltersState] = useState(initialFilters);
  const [resolving, setResolving] = useState<HandoffListItem | null>(null);

  const listKey = queryKeys.handoffs.list(businessId, filters.tab, filters.includeTest);
  const handoffs = useCursorPage<HandoffListItem, HandoffPage>(listKey, ({ cursor, limit }) =>
    api.GET("/v1/businesses/{business_id}/handoffs", {
      params: {
        path: { business_id: businessId },
        query: {
          is_open: isOpenQuery(filters.tab),
          include_sandbox: filters.includeTest ? "true" : undefined,
          limit: String(limit),
          cursor: cursor ?? undefined,
        },
      },
    }),
  );
  // Every load of the list is audited (a view of personal data): no polling,
  // a reload when the user comes back to the tab and the Refresh button.
  useAutoReload(handoffs.reload, { intervalMs: null });
  const resolve = useResolveHandoff(listKey, filters.tab, setResolving);

  const setFilters = (next: HandoffFilters) => {
    setFiltersState(next);
    replaceUrlQuery(handoffFiltersQuery(next));
  };

  const items = handoffs.items ?? [];
  const counts = handoffs.page ? handoffTabCounts(handoffs.page) : null;

  return (
    <>
      <PageHeader
        title={t("navigation.pages.messagesHandoffs")}
        description={t("pages.handoffs.description")}
        actions={<RefreshButton onClick={handoffs.reload} isRefreshing={handoffs.isFetching && handoffs.items !== undefined} />}
      />

      <div className="space-y-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <SegmentedControl
            label={t("handoffs.tabsLabel")}
            value={filters.tab}
            onChange={(tab) => setFilters({ ...filters, tab })}
            options={HANDOFF_TABS.map((tab) => ({
              value: tab,
              label: t(`handoffs.tabs.${tab}`),
              count: counts ? counts[tab] : undefined,
            }))}
          />
          <IncludeTestToggle compact checked={filters.includeTest} onChange={(includeTest) => setFilters({ ...filters, includeTest })} />
        </div>

        {handoffs.error && handoffs.items ? <RefreshFailed error={handoffs.error} onRetry={handoffs.reload} /> : null}
        {handoffs.items === undefined ? (
          handoffs.error ? (
            <Card>
              <ErrorState error={handoffs.error} onRetry={handoffs.reload} />
            </Card>
          ) : (
            <LoadingRegion label={t("handoffs.loading")}>
              <SkeletonCardList cards={3} />
            </LoadingRegion>
          )
        ) : items.length === 0 && !handoffs.isPlaceholder ? (
          <Card>
            <EmptyState
              icon={filters.tab === "open" ? <IconCheck className="size-6" /> : <IconHandoff className="size-6" />}
              title={filters.tab === "open" ? t("handoffs.emptyOpenTitle") : t("handoffs.emptyTitle")}
              description={t("handoffs.emptyOpenDescription")}
            />
          </Card>
        ) : (
          <div
            className={handoffs.isPlaceholder ? "animate-settle opacity-60 transition-opacity" : "animate-settle transition-opacity"}
            aria-busy={handoffs.isPlaceholder || undefined}
          >
            <AnimatedPresenceList
              items={items}
              getKey={(handoff) => handoff.id}
              className="space-y-3"
              renderItem={(handoff) => <HandoffCard handoff={handoff} onResolve={() => setResolving(handoff)} />}
            />
            <LoadMore
              hasMore={handoffs.hasMore}
              isLoading={handoffs.isLoadingMore}
              error={handoffs.moreError}
              onMore={handoffs.loadMore}
              shownText={
                counts && handoffs.hasMore
                  ? t("insights.shownOf", { shown: items.length, total: counts[filters.tab] })
                  : undefined
              }
            />
          </div>
        )}
      </div>

      <ConfirmDialog
        open={resolving !== null}
        tone="primary"
        title={t("handoffs.confirmResolve.title")}
        description={t("handoffs.confirmResolve.description", {
          name: resolving?.contact_name ?? t("insights.unknownCustomer"),
        })}
        confirmLabel={t("handoffs.confirmResolve.confirm")}
        onConfirm={() => {
          if (resolving) {
            void resolve.run(resolving);
          }
        }}
        onClose={() => setResolving(null)}
      />
    </>
  );
}

"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { useApiMutation } from "@/api/hooks";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconCheck, IconHandoff } from "@/components/icons";
import { HandoffStatusBadge, HandoffUrgencyBadge, TestBadge } from "@/components/insights/Badges";
import {
  CustomerName,
  IncludeTestToggle,
  LoadMore,
  PhoneLink,
  RefreshButton,
  RefreshFailed,
} from "@/components/insights/common";
import { ConfirmDialog } from "@/components/insights/ConfirmDialog";
import { formatRelative } from "@/components/insights/dates";
import { isOpenHandoff } from "@/components/insights/handoffs";
import { HANDOFF_REASONS } from "@/components/insights/labels";
import { SegmentedControl } from "@/components/insights/SegmentedControl";
import type { HandoffListItem, HandoffPage } from "@/components/insights/types";
import { useAutoReload } from "@/components/insights/useAutoReload";
import { usePagedQuery } from "@/components/insights/usePagedQuery";
import { replaceUrlQuery } from "@/components/insights/urlQuery";
import { Button, ButtonLink, Card, EmptyState, ErrorState, LoadingBlock, PageHeader, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { businessPath } from "@/lib/navigation";

import {
  afterResolve,
  HANDOFF_TABS,
  handoffFiltersQuery,
  handoffTabCounts,
  isOpenQuery,
  withResolvedCounts,
  type HandoffFilters,
} from "./_components/handoffModel";

const URGENCY_EDGE: Record<HandoffListItem["urgency"], string> = {
  critical: "border-l-danger-solid",
  high: "border-l-warning",
  normal: "border-l-info",
  low: "border-l-line-strong",
};

/**
 * Handoffs (concept /handoffs): conversations the assistant passed to a
 * person, the most urgent open ones first, with the summary, the customer
 * to call back and "resolve" (the assistant answers the customer again).
 */
export function HandoffsScreen({ initialFilters }: { initialFilters: HandoffFilters }) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const businessId = business.id;
  const [filters, setFiltersState] = useState(initialFilters);
  const [resolving, setResolving] = useState<HandoffListItem | null>(null);

  const handoffs = usePagedQuery<HandoffListItem, HandoffPage>(
    ({ cursor, limit }) =>
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
    [businessId, filters.tab, filters.includeTest],
  );
  useAutoReload(handoffs.reload);

  const resolve = useApiMutation((handoff: HandoffListItem) =>
    api.POST("/v1/businesses/{business_id}/handoffs/{handoff_id}/resolve", {
      params: { path: { business_id: businessId, handoff_id: handoff.id } },
    }),
  );

  const setFilters = (next: HandoffFilters) => {
    setFiltersState(next);
    replaceUrlQuery(handoffFiltersQuery(next));
  };

  const runResolve = async () => {
    if (!resolving) {
      return;
    }
    const result = await resolve.run(resolving);
    if (result.ok) {
      const wasOpen = isOpenHandoff(resolving);
      handoffs.updateItems((items) => afterResolve(items, result.data, filters.tab));
      if (wasOpen) {
        handoffs.updatePage(withResolvedCounts);
      }
      toast.success(t("handoffs.resolved"));
      setResolving(null);
    }
  };

  const items = handoffs.items ?? [];
  const counts = handoffs.page ? handoffTabCounts(handoffs.page) : null;

  return (
    <>
      <PageHeader
        title={t("nav.handoffs")}
        description={t("pages.handoffs.description")}
        actions={<RefreshButton onClick={handoffs.reload} isRefreshing={handoffs.isLoading && handoffs.items !== undefined} />}
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
          <Card>
            {handoffs.error ? (
              <ErrorState error={handoffs.error} onRetry={handoffs.reload} />
            ) : (
              <LoadingBlock label={t("handoffs.loading")} />
            )}
          </Card>
        ) : items.length === 0 && !handoffs.isLoading ? (
          <Card>
            <EmptyState
              icon={filters.tab === "open" ? <IconCheck className="size-6" /> : <IconHandoff className="size-6" />}
              title={filters.tab === "open" ? t("handoffs.emptyOpenTitle") : t("handoffs.emptyTitle")}
              description={t("handoffs.emptyOpenDescription")}
            />
          </Card>
        ) : (
          <div className={handoffs.isLoading ? "opacity-60 transition-opacity" : undefined} aria-busy={handoffs.isLoading || undefined}>
            <ul className="space-y-3">
              {items.map((handoff) => (
                <HandoffCard key={handoff.id} handoff={handoff} onResolve={() => setResolving(handoff)} />
              ))}
            </ul>
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
        isPending={resolve.isPending}
        onConfirm={() => void runResolve()}
        onClose={() => setResolving(null)}
      />
    </>
  );
}

function HandoffCard({ handoff, onResolve }: { handoff: HandoffListItem; onResolve: () => void }) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const open = isOpenHandoff(handoff);
  const headingId = `handoff-${handoff.id}`;

  return (
    <li>
      <article
        aria-labelledby={headingId}
        className={cn(
          "rounded-2xl border border-line bg-surface p-4 shadow-sm sm:p-5",
          open && cn("border-l-4", URGENCY_EDGE[handoff.urgency]),
        )}
      >
        <div className="flex flex-wrap items-center gap-2">
          <h2 id={headingId} className="text-base font-semibold text-ink">
            {t(HANDOFF_REASONS[handoff.reason])}
          </h2>
          {open ? <HandoffUrgencyBadge urgency={handoff.urgency} /> : null}
          <HandoffStatusBadge status={handoff.status} />
          {handoff.is_sandbox ? <TestBadge /> : null}
          <span className="text-xs text-ink-subtle sm:ml-auto">
            <time dateTime={new Date(handoff.created_at / 1000).toISOString()} title={format.dateTime(handoff.created_at)}>
              {formatRelative(handoff.created_at, locale) ?? format.dateTime(handoff.created_at)}
            </time>
          </span>
        </div>

        <p dir="auto" className="mt-2 text-sm whitespace-pre-wrap text-ink">
          {handoff.summary}
        </p>

        {handoff.status === "notification_failed" ? (
          <p className="mt-2 text-sm text-danger">{t("handoffs.notificationFailedHint")}</p>
        ) : null}

        <div className="mt-4 flex flex-col gap-3 border-t border-line pt-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
            <span className="font-medium text-ink">
              <CustomerName name={handoff.contact_name} />
            </span>
            {handoff.contact_phone_number ? <PhoneLink phone={handoff.contact_phone_number} /> : null}
            {!open && handoff.resolved_at ? (
              <span className="text-ink-muted">{t("handoffs.resolvedAt", { date: format.dateTime(handoff.resolved_at) })}</span>
            ) : null}
          </p>
          <div className="flex flex-wrap gap-2">
            <ButtonLink
              href={`${businessPath(business.id, "conversations")}/${encodeURIComponent(handoff.conversation_id)}`}
              variant="secondary"
              size="sm"
            >
              {t("insights.openConversation")}
            </ButtonLink>
            {open ? (
              <Button size="sm" leadingIcon={<IconCheck className="size-4" aria-hidden />} onClick={onResolve}>
                {t("handoffs.resolve")}
              </Button>
            ) : null}
          </div>
        </div>
      </article>
    </li>
  );
}

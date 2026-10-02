"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useCursorPage } from "@/api/useCursorPage";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconInbox } from "@/components/icons";
import { CustomerName, IncludeTestToggle, LoadMore, RefreshButton, RefreshFailed } from "@/components/insights/common";
import { LEAD_STATUS, LEAD_STATUSES } from "@/components/insights/labels";
import { SegmentedControl } from "@/components/insights/SegmentedControl";
import type { LeadListItem, LeadPage } from "@/components/insights/types";
import { replaceUrlQuery } from "@/components/insights/urlQuery";
import { Button, Card, EmptyState, ErrorState, LoadingRegion, Modal, PageHeader, SkeletonCardList } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { countsByTab, leadFiltersQuery, type LeadFilters, type LeadTab } from "./_components/leadModel";
import { LeadCard } from "./_components/LeadCard";
import { LeadDetails } from "./_components/LeadDetails";
import { useLeadStatus } from "./_components/useLeadStatus";

/**
 * Leads (concept /leads): requests the assistant passed to a manager —
 * banquets, groups, orders — with their status, moved by staff.
 */
export function LeadsScreen({ initialFilters }: { initialFilters: LeadFilters }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const businessId = business.id;
  const [filters, setFiltersState] = useState(initialFilters);
  const [openId, setOpenId] = useState<string | null>(null);

  const listKey = queryKeys.leads.list(businessId, filters.tab, filters.includeTest);
  const leads = useCursorPage<LeadListItem, LeadPage>(listKey, ({ cursor, limit }) =>
    api.GET("/v1/businesses/{business_id}/leads", {
      params: {
        path: { business_id: businessId },
        query: {
          status: filters.tab === "all" ? undefined : filters.tab,
          include_sandbox: filters.includeTest ? "true" : undefined,
          limit: String(limit),
          cursor: cursor ?? undefined,
        },
      },
    }),
  );
  const status = useLeadStatus(listKey, filters.tab);

  const setFilters = (next: LeadFilters) => {
    setFiltersState(next);
    replaceUrlQuery(leadFiltersQuery(next));
  };

  const items = leads.items ?? [];
  const counts = leads.page ? countsByTab(leads.page.status_counts ?? []) : null;
  const openLead = items.find((lead) => lead.id === openId) ?? null;
  const tabs: LeadTab[] = ["all", ...LEAD_STATUSES];

  return (
    <>
      <PageHeader
        title={t("nav.leads")}
        description={t("pages.leads.description")}
        actions={<RefreshButton onClick={leads.reload} isRefreshing={leads.isFetching && leads.items !== undefined} />}
      />

      <div className="space-y-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <SegmentedControl
            label={t("leads.tabsLabel")}
            value={filters.tab}
            onChange={(tab) => setFilters({ ...filters, tab })}
            options={tabs.map((tab) => ({
              value: tab,
              label: tab === "all" ? t("insights.all") : t(LEAD_STATUS[tab].label),
              count: counts ? counts[tab] : undefined,
            }))}
          />
          <IncludeTestToggle compact checked={filters.includeTest} onChange={(includeTest) => setFilters({ ...filters, includeTest })} />
        </div>

        {leads.error && leads.items ? <RefreshFailed error={leads.error} onRetry={leads.reload} /> : null}
        {leads.items === undefined ? (
          leads.error ? (
            <Card>
              <ErrorState error={leads.error} onRetry={leads.reload} />
            </Card>
          ) : (
            <LoadingRegion label={t("leads.loading")}>
              <SkeletonCardList cards={4} />
            </LoadingRegion>
          )
        ) : items.length === 0 && !leads.isPlaceholder ? (
          <Card>
            <EmptyState
              icon={<IconInbox className="size-6" />}
              title={counts?.all === 0 ? t("leads.emptyTitle") : t("insights.noMatchesTitle")}
              description={counts?.all === 0 ? t("leads.emptyDescription") : t("insights.noMatchesDescription")}
            />
          </Card>
        ) : (
          <div
            className={leads.isPlaceholder ? "opacity-60 transition-opacity" : "animate-settle"}
            aria-busy={leads.isPlaceholder || undefined}
          >
            <ul className="space-y-3">
              {items.map((lead) => (
                <LeadCard
                  key={lead.id}
                  lead={lead}
                  isPending={status.isPending(lead.id)}
                  onStatus={(next) => void status.changeStatus(lead, next)}
                  onOpen={() => setOpenId(lead.id)}
                />
              ))}
            </ul>
            <LoadMore
              hasMore={leads.hasMore}
              isLoading={leads.isLoadingMore}
              error={leads.moreError}
              onMore={leads.loadMore}
              shownText={
                counts && leads.hasMore
                  ? t("insights.shownOf", { shown: items.length, total: counts[filters.tab] })
                  : undefined
              }
            />
          </div>
        )}
      </div>

      <Modal
        open={openLead !== null}
        onClose={() => setOpenId(null)}
        title={openLead ? <CustomerName name={openLead.contact_name} /> : t("leads.details")}
        footer={
          <Button variant="secondary" onClick={() => setOpenId(null)}>
            {t("common.close")}
          </Button>
        }
      >
        {openLead ? (
          <LeadDetails
            lead={openLead}
            isPending={status.isPending(openLead.id)}
            onStatus={(next) => void status.changeStatus(openLead, next)}
          />
        ) : null}
      </Modal>
    </>
  );
}


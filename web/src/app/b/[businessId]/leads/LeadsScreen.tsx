"use client";

import Link from "next/link";
import { useState } from "react";

import { api } from "@/api/client";
import { useApiMutation } from "@/api/hooks";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconInbox } from "@/components/icons";
import { ChannelBadge, LeadStatusBadge, LeadTypeBadge, TestBadge } from "@/components/insights/Badges";
import {
  CustomerName,
  DetailRow,
  IncludeTestToggle,
  LoadMore,
  PhoneLink,
  RefreshButton,
  RefreshFailed,
} from "@/components/insights/common";
import { formatLocalDate, formatRelative } from "@/components/insights/dates";
import { LEAD_STATUS, LEAD_STATUSES } from "@/components/insights/labels";
import { SegmentedControl } from "@/components/insights/SegmentedControl";
import type { LeadListItem, LeadPage, LeadStatus } from "@/components/insights/types";
import { replaceUrlQuery } from "@/components/insights/urlQuery";
import { usePagedQuery } from "@/components/insights/usePagedQuery";
import { Button, Card, EmptyState, ErrorState, LoadingBlock, Modal, PageHeader, Select, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import {
  afterStatusChange,
  countsByTab,
  leadFiltersQuery,
  withStatusCounts,
  type LeadFilters,
  type LeadTab,
} from "./_components/leadModel";

/**
 * Leads (concept /leads): requests the assistant passed to a manager —
 * banquets, groups, orders — with their status, moved by staff.
 */
export function LeadsScreen({ initialFilters }: { initialFilters: LeadFilters }) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const businessId = business.id;
  const [filters, setFiltersState] = useState(initialFilters);
  const [openId, setOpenId] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);

  const leads = usePagedQuery<LeadListItem, LeadPage>(
    ({ cursor, limit }) =>
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
    [businessId, filters.tab, filters.includeTest],
  );

  const update = useApiMutation((lead: LeadListItem, status: LeadStatus) =>
    api.PATCH("/v1/businesses/{business_id}/leads/{lead_id}", {
      params: { path: { business_id: businessId, lead_id: lead.id } },
      body: { status },
    }),
  );

  const setFilters = (next: LeadFilters) => {
    setFiltersState(next);
    replaceUrlQuery(leadFiltersQuery(next));
  };

  const changeStatus = async (lead: LeadListItem, status: LeadStatus) => {
    if (status === lead.status) {
      return;
    }
    setPendingId(lead.id);
    const result = await update.run(lead, status);
    setPendingId(null);
    if (result.ok) {
      leads.updateItems((items) => afterStatusChange(items, lead.id, result.data.status, filters.tab));
      leads.updatePage((page) => withStatusCounts(page, lead.status, result.data.status));
      toast.success(t("leads.updated", { status: t(LEAD_STATUS[result.data.status].label) }));
    }
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
        actions={<RefreshButton onClick={leads.reload} isRefreshing={leads.isLoading && leads.items !== undefined} />}
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
          <Card>
            {leads.error ? <ErrorState error={leads.error} onRetry={leads.reload} /> : <LoadingBlock label={t("leads.loading")} />}
          </Card>
        ) : items.length === 0 && !leads.isLoading ? (
          <Card>
            <EmptyState
              icon={<IconInbox className="size-6" />}
              title={counts?.all === 0 ? t("leads.emptyTitle") : t("insights.noMatchesTitle")}
              description={counts?.all === 0 ? t("leads.emptyDescription") : t("insights.noMatchesDescription")}
            />
          </Card>
        ) : (
          <div className={leads.isLoading ? "opacity-60 transition-opacity" : undefined} aria-busy={leads.isLoading || undefined}>
            <ul className="space-y-3">
              {items.map((lead) => (
                <LeadCard
                  key={lead.id}
                  lead={lead}
                  isPending={pendingId === lead.id}
                  onStatus={(status) => void changeStatus(lead, status)}
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
            isPending={pendingId === openLead.id}
            onStatus={(status) => void changeStatus(openLead, status)}
          />
        ) : null}
      </Modal>
    </>
  );
}

function StatusSelect({
  lead,
  isPending,
  onStatus,
  label,
}: {
  lead: LeadListItem;
  isPending: boolean;
  onStatus: (status: LeadStatus) => void;
  label: string;
}) {
  const { t } = useI18n();
  return (
    <Select
      aria-label={label}
      value={lead.status}
      disabled={isPending}
      aria-busy={isPending || undefined}
      onChange={(event) => onStatus(event.target.value as LeadStatus)}
      className="w-full sm:w-44"
    >
      {LEAD_STATUSES.map((status) => (
        <option key={status} value={status}>
          {t(LEAD_STATUS[status].label)}
        </option>
      ))}
    </Select>
  );
}

function LeadMeta({ lead }: { lead: LeadListItem }) {
  const { t, tp, locale } = useI18n();
  const parts = [
    lead.requested_date ? `${t("leads.requestedDate")}: ${formatLocalDate(lead.requested_date, locale)}` : null,
    lead.party_size ? tp("bookings.guests", lead.party_size) : null,
  ].filter(Boolean);
  return (
    <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-muted">
      {parts.length > 0 ? <span>{parts.join(" · ")}</span> : null}
      {lead.budget ? (
        <span>
          {t("leads.budget")}: <span dir="auto">{lead.budget}</span>
        </span>
      ) : null}
    </p>
  );
}

function LeadCard({
  lead,
  isPending,
  onStatus,
  onOpen,
}: {
  lead: LeadListItem;
  isPending: boolean;
  onStatus: (status: LeadStatus) => void;
  onOpen: () => void;
}) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const name = lead.contact_name ?? t("insights.unknownCustomer");
  return (
    <li className="rounded-2xl border border-line bg-surface p-4 shadow-sm sm:p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <LeadTypeBadge type={lead.lead_type} />
            <LeadStatusBadge status={lead.status} />
            {lead.is_sandbox ? <TestBadge /> : null}
            <span className="text-xs text-ink-subtle">
              {formatRelative(lead.created_at, locale) ?? format.date(lead.created_at)}
            </span>
          </div>
          <p dir="auto" className="line-clamp-3 text-sm whitespace-pre-wrap text-ink">
            {lead.details}
          </p>
          <LeadMeta lead={lead} />
          <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
            <span className="font-medium text-ink">
              <CustomerName name={lead.contact_name} />
            </span>
            {lead.contact_phone_number ? <PhoneLink phone={lead.contact_phone_number} /> : null}
          </p>
        </div>
        <div className="flex shrink-0 flex-col gap-2 sm:items-end">
          <StatusSelect lead={lead} isPending={isPending} onStatus={onStatus} label={t("leads.statusOf", { name })} />
          <Button variant="ghost" size="sm" onClick={onOpen}>
            {t("leads.showDetails")}
          </Button>
        </div>
      </div>
    </li>
  );
}

function LeadDetails({
  lead,
  isPending,
  onStatus,
}: {
  lead: LeadListItem;
  isPending: boolean;
  onStatus: (status: LeadStatus) => void;
}) {
  const { t, tp, locale } = useI18n();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <LeadTypeBadge type={lead.lead_type} />
        {lead.is_sandbox ? <TestBadge /> : null}
      </div>
      <p dir="auto" className="rounded-xl bg-surface-muted px-4 py-3 text-sm whitespace-pre-wrap text-ink">
        {lead.details}
      </p>
      <dl className="divide-y divide-line">
        <DetailRow label={t("leads.statusLabel")}>
          <StatusSelect lead={lead} isPending={isPending} onStatus={onStatus} label={t("leads.statusLabel")} />
        </DetailRow>
        {lead.requested_date ? (
          <DetailRow label={t("leads.requestedDate")}>
            {formatLocalDate(lead.requested_date, locale, { dateStyle: "full" })}
          </DetailRow>
        ) : null}
        {lead.party_size ? <DetailRow label={t("leads.partySize")}>{tp("bookings.guests", lead.party_size)}</DetailRow> : null}
        {lead.budget ? (
          <DetailRow label={t("leads.budget")}>
            <span dir="auto">{lead.budget}</span>
          </DetailRow>
        ) : null}
        <DetailRow label={t("leads.contact")}>
          <span className="flex flex-wrap items-center gap-x-3">
            <CustomerName name={lead.contact_name} />
            {lead.contact_phone_number ? <PhoneLink phone={lead.contact_phone_number} /> : null}
          </span>
        </DetailRow>
        <DetailRow label={t("leads.source")}>
          <ChannelBadge channel={lead.source_channel} />
        </DetailRow>
        <DetailRow label={t("leads.received")}>{format.dateTime(lead.created_at)}</DetailRow>
      </dl>
      {lead.conversation_id ? (
        <Link
          href={`${businessPath(business.id, "conversations")}/${encodeURIComponent(lead.conversation_id)}`}
          className="inline-flex text-sm font-medium text-accent hover:underline"
        >
          {t("insights.openConversation")}
        </Link>
      ) : null}
    </div>
  );
}

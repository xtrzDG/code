"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { LeadStatusBadge, LeadTypeBadge, TestBadge } from "@/components/insights/Badges";
import { CustomerName, PhoneLink } from "@/components/insights/common";
import { formatLocalDate, formatRelative } from "@/components/insights/dates";
import type { LeadListItem, LeadStatus } from "@/components/insights/types";
import { Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { LeadStatusSelect } from "./LeadStatusSelect";

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

/** One lead in the list: type, status, when, what was asked, the customer, and the status select. */
export function LeadCard({
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
          <LeadStatusSelect lead={lead} isPending={isPending} onStatus={onStatus} label={t("leads.statusOf", { name })} />
          <Button variant="ghost" size="sm" onClick={onOpen}>
            {t("leads.showDetails")}
          </Button>
        </div>
      </div>
    </li>
  );
}

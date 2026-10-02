"use client";

import Link from "next/link";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { ChannelBadge, LeadTypeBadge, TestBadge } from "@/components/insights/Badges";
import { CustomerName, DetailRow, PhoneLink } from "@/components/insights/common";
import { formatLocalDate } from "@/components/insights/dates";
import type { LeadListItem, LeadStatus } from "@/components/insights/types";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import { LeadStatusSelect } from "./LeadStatusSelect";

/** A lead in full: what was asked, its status, date, party, budget, contact, source and conversation. */
export function LeadDetails({
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
          <LeadStatusSelect lead={lead} isPending={isPending} onStatus={onStatus} label={t("leads.statusLabel")} />
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

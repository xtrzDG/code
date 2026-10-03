"use client";

/**
 * What waits in this conversation, above the transcript: why the
 * assistant called for a person (with its summary and urgency) and the
 * open requests with their status, changed right here. Resolving is in
 * the quick actions at the foot, next to the reply.
 */

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { HandoffUrgencyBadge, LeadTypeBadge } from "@/components/insights/Badges";
import { formatLocalDate, formatRelative } from "@/components/insights/dates";
import { HANDOFF_REASONS } from "@/components/insights/labels";
import type { HandoffListItem, LeadListItem, LeadStatus } from "@/components/insights/types";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { handoffSummary } from "../../_lib/handoffSummary";
import { LeadStatusSelect } from "../details/LeadStatusSelect";

const URGENCY_EDGE = {
  critical: "border-s-danger-solid",
  high: "border-s-warning",
  normal: "border-s-info",
  low: "border-s-line-strong",
} as const;

function HandoffWork({ handoff }: { handoff: HandoffListItem }) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const summary = handoffSummary(handoff, t);
  const since = formatRelative(handoff.created_at, locale) ?? format.dateTime(handoff.created_at);
  return (
    <section
      aria-label={t("inboxCard.work.needsPerson")}
      className={cn("rounded-2xl border border-line border-s-4 bg-surface px-4 py-3 shadow-sm", URGENCY_EDGE[handoff.urgency])}
    >
      <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
        <span className="font-semibold text-ink">{t(HANDOFF_REASONS[handoff.reason])}</span>
        <HandoffUrgencyBadge urgency={handoff.urgency} />
        <span className="text-xs text-ink-subtle">{t("inboxCard.work.since", { time: since })}</span>
      </p>
      <p dir="auto" className="mt-1 line-clamp-3 text-sm break-words text-ink-muted">
        {summary.text}
      </p>
      {summary.quote ? (
        <figure className="mt-2 rounded-xl border-s-2 border-line-strong bg-surface-muted/60 px-3 py-1.5">
          <figcaption className="text-xs text-ink-subtle">{summary.quote.label}</figcaption>
          <blockquote dir="auto" className="text-sm break-words text-ink">
            {summary.quote.text}
          </blockquote>
        </figure>
      ) : null}
      <p className="mt-1.5 text-xs text-ink-subtle">{t("conversations.handoffNotice")}</p>
      {handoff.status === "notification_failed" ? (
        <p className="mt-1.5 text-sm text-danger">{t("handoffs.notificationFailedHint")}</p>
      ) : null}
    </section>
  );
}

function RequestWork({
  lead,
  isPending,
  onStatus,
}: {
  lead: LeadListItem;
  isPending: boolean;
  onStatus: (status: LeadStatus) => void;
}) {
  const { t, tp, locale } = useI18n();
  const facts = [
    lead.requested_date ? formatLocalDate(lead.requested_date, locale, { weekday: "short", day: "numeric", month: "short" }) : null,
    lead.party_size ? tp("bookings.guests", lead.party_size) : null,
  ].filter(Boolean);
  return (
    <section
      aria-label={t("inboxCard.work.request")}
      className="flex flex-col gap-2 rounded-2xl border border-line border-s-4 border-s-accent bg-surface px-4 py-3 shadow-sm sm:flex-row sm:items-center"
    >
      <div className="min-w-0 flex-1">
        <p className="flex flex-wrap items-center gap-2 text-sm">
          <LeadTypeBadge type={lead.lead_type} />
          {facts.length > 0 ? <span className="text-ink-muted">{facts.join(" · ")}</span> : null}
        </p>
        <p dir="auto" className="mt-1 line-clamp-2 text-sm break-words text-ink">
          {lead.details}
        </p>
      </div>
      <LeadStatusSelect lead={lead} isPending={isPending} onStatus={onStatus} label={t("inboxCard.work.requestStatus")} />
    </section>
  );
}

export function WorkStrip({
  handoff,
  requests,
  isRequestPending,
  onRequestStatus,
}: {
  handoff: HandoffListItem | null;
  requests: readonly LeadListItem[];
  isRequestPending: (leadId: string) => boolean;
  onRequestStatus: (lead: LeadListItem, status: LeadStatus) => void;
}) {
  if (!handoff && requests.length === 0) {
    return null;
  }
  return (
    <div className="space-y-2">
      {handoff ? <HandoffWork handoff={handoff} /> : null}
      {requests.map((lead) => (
        <RequestWork
          key={lead.id}
          lead={lead}
          isPending={isRequestPending(lead.id)}
          onStatus={(status) => onRequestStatus(lead, status)}
        />
      ))}
    </div>
  );
}

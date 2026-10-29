"use client";

/**
 * A customer's history across channels, the latest first (upcoming
 * bookings lead): conversations, bookings, requests and calls, each with
 * its status, and a link to the conversation it came from.
 */

import Link from "next/link";
import type { ReactNode } from "react";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconCalendar, IconChat, IconClipboard, IconPhone } from "@/components/icons";
import { BookingStatusBadge, ConversationStatusBadge, LeadStatusBadge, LeadTypeBadge } from "@/components/insights/Badges";
import { CHANNEL_LABELS } from "@/components/insights/labels";
import { Badge, Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { conversationPath } from "@/lib/navigation";

import { CALL_OUTCOMES } from "../../../inbox/_lib/conversationModel";
import type { TimelineEntry } from "../../_lib/customerModel";

const MICROSECONDS_PER_SECOND = 1_000_000;

const KIND_LABELS: Record<TimelineEntry["kind"], MessageKey> = {
  conversation: "customers.timeline.conversation",
  booking: "customers.timeline.booking",
  lead: "customers.timeline.lead",
  call: "customers.timeline.call",
};

const KIND_ICONS: Record<TimelineEntry["kind"], ReactNode> = {
  conversation: <IconChat className="size-4" aria-hidden />,
  booking: <IconCalendar className="size-4" aria-hidden />,
  lead: <IconClipboard className="size-4" aria-hidden />,
  call: <IconPhone className="size-4" aria-hidden />,
};

function entryKey(entry: TimelineEntry): string {
  return `${entry.kind}:${entry.conversation_id ?? ""}:${entry.booking_id ?? ""}:${entry.lead_id ?? ""}:${entry.call_id ?? ""}`;
}

function EntryBadges({ entry }: { entry: TimelineEntry }) {
  const { t } = useI18n();
  return (
    <>
      {entry.channel ? <Badge tone="neutral">{t(CHANNEL_LABELS[entry.channel])}</Badge> : null}
      {entry.conversation_status ? <ConversationStatusBadge status={entry.conversation_status} /> : null}
      {entry.booking_status ? <BookingStatusBadge status={entry.booking_status} /> : null}
      {entry.lead_type ? <LeadTypeBadge type={entry.lead_type} /> : null}
      {entry.lead_status ? <LeadStatusBadge status={entry.lead_status} /> : null}
      {entry.call_outcome ? <Badge tone="neutral">{t(CALL_OUTCOMES[entry.call_outcome])}</Badge> : null}
    </>
  );
}

function TimelineItem({ entry }: { entry: TimelineEntry }) {
  const { t, tp } = useI18n();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const detail =
    entry.kind === "booking" && typeof entry.starts_at === "number"
      ? t("customers.timeline.bookingAt", {
          date: format.dateTime(entry.starts_at * MICROSECONDS_PER_SECOND),
          guests: tp("customers.timeline.guests", entry.party_size ?? 1),
        })
      : entry.kind === "call" && typeof entry.duration_seconds === "number"
        ? tp("customers.timeline.callLength", Math.max(1, Math.round(entry.duration_seconds / 60)))
        : null;

  return (
    <li className="group relative flex gap-3 pb-5 last:pb-0">
      <span aria-hidden className="absolute start-4 top-8 bottom-0 w-px bg-line group-last:hidden" />
      <span className="relative flex size-8 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent-ink">
        {KIND_ICONS[entry.kind]}
      </span>
      <div className="min-w-0 flex-1 pt-1">
        <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="text-sm font-medium text-ink">{t(KIND_LABELS[entry.kind])}</span>
          <EntryBadges entry={entry} />
        </p>
        {entry.kind !== "booking" ? (
          <p className="mt-0.5 text-xs text-ink-subtle">{format.dateTime(entry.occurred_at)}</p>
        ) : null}
        {detail ? <p className="mt-0.5 text-xs text-ink-muted">{detail}</p> : null}
        {entry.summary ? (
          <p dir="auto" data-user-content className="mt-1 text-sm text-ink-muted">
            {entry.summary}
          </p>
        ) : null}
        {entry.conversation_id ? (
          <Link
            href={conversationPath(business.id, entry.conversation_id)}
            className="mt-1 inline-block text-xs font-medium text-accent hover:underline"
          >
            {t("customers.timeline.openConversation")}
          </Link>
        ) : null}
      </div>
    </li>
  );
}

export function CustomerTimeline({ entries }: { entries: readonly TimelineEntry[] }) {
  const { t } = useI18n();
  return (
    <Card title={t("customers.timeline.title")} description={t("customers.timeline.description")}>
      {entries.length === 0 ? (
        <p className="text-sm text-ink-muted">{t("customers.timeline.empty")}</p>
      ) : (
        <ol aria-label={t("customers.timeline.title")}>
          {entries.map((entry) => (
            <TimelineItem key={entryKey(entry)} entry={entry} />
          ))}
        </ol>
      )}
    </Card>
  );
}

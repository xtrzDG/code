"use client";

import { IconMoon } from "@/components/icons";
import { Badge } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import {
  BOOKING_STATUS,
  CHANNEL_LABELS,
  CONVERSATION_STATUS,
  HANDOFF_STATUS,
  HANDOFF_URGENCY,
  LEAD_STATUS,
  LEAD_TYPES,
  type StatusLabel,
} from "./labels";
import type {
  BookingStatus,
  ChannelKind,
  ConversationStatus,
  HandoffStatus,
  HandoffUrgency,
  LeadStatus,
  LeadType,
} from "./types";

function StatusBadge({ entry }: { entry: StatusLabel }) {
  const { t } = useI18n();
  return <Badge tone={entry.tone}>{t(entry.label)}</Badge>;
}

export function ChannelBadge({ channel }: { channel: ChannelKind }) {
  const { t } = useI18n();
  return <Badge tone="neutral">{t(CHANNEL_LABELS[channel])}</Badge>;
}

export function ConversationStatusBadge({ status }: { status: ConversationStatus }) {
  return <StatusBadge entry={CONVERSATION_STATUS[status]} />;
}

export function BookingStatusBadge({ status }: { status: BookingStatus }) {
  return <StatusBadge entry={BOOKING_STATUS[status]} />;
}

export function LeadStatusBadge({ status }: { status: LeadStatus }) {
  return <StatusBadge entry={LEAD_STATUS[status]} />;
}

export function LeadTypeBadge({ type }: { type: LeadType }) {
  const { t } = useI18n();
  return <Badge tone="neutral">{t(LEAD_TYPES[type])}</Badge>;
}

export function HandoffUrgencyBadge({ urgency }: { urgency: HandoffUrgency }) {
  return <StatusBadge entry={HANDOFF_URGENCY[urgency]} />;
}

export function HandoffStatusBadge({ status }: { status: HandoffStatus }) {
  return <StatusBadge entry={HANDOFF_STATUS[status]} />;
}

/** Marks owner test-chat and autotest activity. */
export function TestBadge() {
  const { t } = useI18n();
  return <Badge tone="info">{t("insights.testBadge")}</Badge>;
}

export function AfterHoursBadge() {
  const { t } = useI18n();
  return (
    <Badge tone="neutral" icon={<IconMoon className="size-3.5" aria-hidden />}>
      {t("insights.afterHours")}
    </Badge>
  );
}

"use client";

/**
 * The small parts of an inbox row: the channel's glyph, the short age of
 * the last message, the reason chip, the preview, and the row's details
 * (who handles it, where the customer came from, after hours, notes, the
 * exact time) that the hover card shows and screen readers hear.
 */

import type { ComponentType, ReactNode } from "react";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import {
  IconChat,
  IconFlask,
  IconInstagram,
  IconMessenger,
  IconMoon,
  IconPencil,
  IconPhone,
  IconTelegram,
  IconWhatsApp,
  IconWindow,
  type IconProps,
} from "@/components/icons";
import { CHANNEL_LABELS, HANDOFF_REASONS, HANDOFF_URGENCY, LEAD_TYPES, MESSAGE_AUTHORS } from "@/components/insights/labels";
import type { ChannelKind } from "@/components/insights/types";
import { Badge } from "@/components/ui";
import { sourceLabel } from "@/components/value/sourceLabel";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import type { InboxRow } from "../../_lib/inboxModel";
import { ATTACHMENT_KIND_LABELS } from "../../_lib/messageMedia";
import { rowAge } from "../../_lib/rowAge";
import type { TeamMember } from "../../_lib/team";
import { ATTACHMENT_ICONS } from "../attachmentIcons";
import { MemberAvatar } from "../MemberAvatar";

const CHANNEL_GLYPHS: Record<ChannelKind, ComponentType<IconProps>> = {
  phone: IconPhone,
  whatsapp: IconWhatsApp,
  instagram: IconInstagram,
  messenger: IconMessenger,
  telegram: IconTelegram,
  web_chat: IconWindow,
  viber: IconChat,
  owner_test: IconFlask,
};

/** The channel as a glyph (its name for screen readers). */
export function ChannelGlyph({ channel, className }: { channel: ChannelKind; className?: string }) {
  const { t } = useI18n();
  const Glyph = CHANNEL_GLYPHS[channel];
  return (
    <span className={cn("inline-flex shrink-0", className)} title={t(CHANNEL_LABELS[channel])}>
      <Glyph className="size-3.5" aria-hidden />
      <span className="sr-only">{t(CHANNEL_LABELS[channel])}</span>
    </span>
  );
}

/** "now", "5 min", "3 h", "2 d", else the date. */
export function RowAgeText({ at, nowMs }: { at: number; nowMs: number }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const age = rowAge(at, nowMs);
  const text = age === null ? format.date(at) : age.unit === "now" ? t("inboxTriage.age.now") : t(`inboxTriage.age.${age.unit}`, { count: age.count });
  return <time dateTime={new Date(at / 1000).toISOString()}>{text}</time>;
}

/** Why the conversation waits: the handoff's reason (its urgency colours it), else the open request. */
export function WorkChip({ row, className }: { row: InboxRow; className?: string }) {
  const { t } = useI18n();
  if (row.handoff) {
    return (
      <Badge tone={HANDOFF_URGENCY[row.handoff.urgency].tone} className={cn("min-w-0", className)}>
        <span className="truncate">{t(HANDOFF_REASONS[row.handoff.reason])}</span>
      </Badge>
    );
  }
  if (row.request) {
    return (
      <Badge tone="accent" className={cn("min-w-0", className)}>
        <span className="truncate">{t("inbox.row.request", { type: t(LEAD_TYPES[row.request.lead_type]) })}</span>
      </Badge>
    );
  }
  return null;
}

/** The beginning of the last message on one line: who wrote it (not the customer), a media mark, the text. */
export function RowPreview({ row, className }: { row: InboxRow; className?: string }) {
  const { t } = useI18n();
  if (!row.lastMessageText && !row.lastMessageAttachment) {
    return <span className={className} />;
  }
  const Media = row.lastMessageAttachment ? ATTACHMENT_ICONS[row.lastMessageAttachment] : null;
  return (
    <span className={cn("min-w-0 truncate", className)} data-clip="content">
      {row.lastMessageAuthor && row.lastMessageAuthor !== "customer" ? (
        <span className="text-ink-subtle">{t(MESSAGE_AUTHORS[row.lastMessageAuthor])}: </span>
      ) : null}
      {Media && row.lastMessageAttachment ? (
        <>
          <Media className="me-1 inline-block size-3.5 align-[-2px] text-ink-subtle" aria-hidden />
          <span className={row.lastMessageText ? "sr-only" : undefined}>
            {t(ATTACHMENT_KIND_LABELS[row.lastMessageAttachment])}
            {row.lastMessageText ? ": " : null}
          </span>
        </>
      ) : null}
      {row.lastMessageText ? <bdi data-user-content>{row.lastMessageText}</bdi> : null}
    </span>
  );
}

/** The team's notes, as a pencil and their number. */
export function NotesMark({ count }: { count: number }) {
  const { tp } = useI18n();
  if (count <= 0) {
    return null;
  }
  return (
    <span className="inline-flex shrink-0 items-center gap-0.5 text-xs text-warning">
      <IconPencil className="size-3.5" aria-hidden />
      <span aria-hidden>{count}</span>
      <span className="sr-only">{tp("inbox.row.notes", count)}</span>
    </span>
  );
}

/** Who handles the row: you, a teammate (user content), a former member, or nobody where someone is needed. */
function AssigneeValue({ row, member }: { row: InboxRow; member: TeamMember | null }) {
  const { t } = useI18n();
  if (row.assigneeUserId === null) {
    return <span className="text-ink-subtle">{t("inbox.row.unassigned")}</span>;
  }
  const userName = member && !member.isMe ? member.name : null;
  return (
    <span className="inline-flex min-w-0 items-center gap-1.5">
      <MemberAvatar member={member ?? { initials: "#", tone: 0 }} size="xs" />
      <span className="truncate" data-user-content={userName ? true : undefined}>
        {member?.isMe ? t("inbox.row.you") : (userName ?? t("inbox.assign.teammate"))}
      </span>
    </span>
  );
}

/** One detail: its name over its value. */
function Detail({ label, children }: { label: string; children: ReactNode }) {
  return (
    <span className="block min-w-0">
      <span className="block text-[0.6875rem] font-medium tracking-wide text-ink-subtle uppercase">{label}</span>
      <span className="block min-w-0 break-words text-ink">{children}</span>
    </span>
  );
}

/**
 * What the row no longer shows on its face: who handles it, where the
 * customer came from, after hours, notes and the exact time of the last
 * message. Each name over its value, for the hover card and (read in the
 * row's link) for screen readers.
 */
export function RowDetails({ row, member, className }: { row: InboxRow; member: TeamMember | null; className?: string }) {
  const { t, tp } = useI18n();
  const format = useBusinessFormat();
  const showsAssignee = row.assigneeUserId !== undefined && (row.assigneeUserId !== null || row.handoff || row.request);
  return (
    <span className={cn("flex flex-col gap-2", className)}>
      {showsAssignee ? (
        <Detail label={t("inboxTriage.details.assignee")}>
          <AssigneeValue row={row} member={member} />
        </Detail>
      ) : null}
      {row.acquisitionSource ? <Detail label={t("inboxTriage.details.source")}>{sourceLabel(row.acquisitionSource, t)}</Detail> : null}
      <Detail label={t("inboxTriage.details.lastMessage")}>
        <span className="tabular-nums">{format.dateTime(row.lastMessageAt)}</span>
      </Detail>
      {row.isAfterHours || row.noteCount > 0 ? (
        <span className="flex flex-wrap gap-x-3 gap-y-1">
          {row.isAfterHours ? (
            <span className="inline-flex items-center gap-1.5 text-ink-muted">
              <IconMoon className="size-3.5" aria-hidden />
              {t("insights.afterHours")}
            </span>
          ) : null}
          {row.noteCount > 0 ? (
            <span className="inline-flex items-center gap-1.5 text-warning">
              <IconPencil className="size-3.5" aria-hidden />
              {tp("inbox.row.notes", row.noteCount)}
            </span>
          ) : null}
        </span>
      ) : null}
    </span>
  );
}

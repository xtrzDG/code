"use client";

/**
 * One conversation of the inbox: the customer, when, the beginning of the
 * last message, and what waits in it: why a person is needed (its urgency
 * colours the edge), the open request, who handles it and the team's
 * notes. The whole row opens the conversation.
 */

import Link from "next/link";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconPencil } from "@/components/icons";
import { AfterHoursBadge, TestBadge } from "@/components/insights/Badges";
import { CustomerName } from "@/components/insights/common";
import { formatRelative } from "@/components/insights/dates";
import { CHANNEL_LABELS, HANDOFF_REASONS, HANDOFF_URGENCY, LEAD_TYPES, MESSAGE_AUTHORS } from "@/components/insights/labels";
import { Badge } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { conversationPath } from "@/lib/navigation";

import { initialsOf } from "../../_lib/conversationModel";
import type { InboxRow } from "../../_lib/inboxModel";
import type { TeamMember } from "../../_lib/team";
import { MemberAvatar } from "../MemberAvatar";

const URGENCY_EDGE = {
  critical: "before:bg-danger-solid",
  high: "before:bg-warning",
  normal: "before:bg-info",
  low: "before:bg-line-strong",
} as const;

function Assignee({ row, member }: { row: InboxRow; member: TeamMember | null }) {
  const { t } = useI18n();
  if (row.assigneeUserId === undefined) {
    return null;
  }
  if (row.assigneeUserId === null) {
    // Only worth saying where someone is needed.
    return row.handoff || row.request ? <span className="text-ink-subtle">{t("inbox.row.unassigned")}</span> : null;
  }
  const name = member?.isMe ? t("inbox.row.you") : (member?.name ?? t("inbox.assign.teammate"));
  return (
    <span className="inline-flex min-w-0 items-center gap-1.5">
      <MemberAvatar member={member ?? { initials: "#", tone: 0 }} size="xs" />
      <span className="sr-only">{t("inbox.row.assignedTo", { name })}</span>
      <span aria-hidden className="truncate">
        {name}
      </span>
    </span>
  );
}

export function InboxRowItem({
  row,
  member,
  isSelected,
  linkQuery,
}: {
  row: InboxRow;
  /** Who handles it (null: nobody, or a former member). */
  member: TeamMember | null;
  isSelected: boolean;
  linkQuery: string;
}) {
  const { t, tp, locale } = useI18n();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const href = `${conversationPath(business.id, row.id)}${linkQuery ? `?${linkQuery}` : ""}`;
  const when = formatRelative(row.lastMessageAt, locale, { maxDays: 1 }) ?? format.date(row.lastMessageAt);

  return (
    <li>
      <Link
        href={href}
        aria-current={isSelected ? "page" : undefined}
        className={cn(
          "relative flex gap-3 px-4 py-3.5 transition-colors focus-visible:-outline-offset-2",
          "before:absolute before:inset-y-2 before:start-0 before:w-1 before:rounded-full",
          row.handoff ? URGENCY_EDGE[row.handoff.urgency] : "before:bg-transparent",
          isSelected ? "bg-accent-soft" : "hover:bg-surface-muted active:bg-surface-muted",
        )}
      >
        <span
          className="flex size-10 shrink-0 items-center justify-center rounded-full bg-surface-muted text-sm font-semibold text-ink-muted"
          aria-hidden
        >
          {initialsOf(row.contactName)}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-baseline justify-between gap-2">
            <span className="min-w-0 truncate text-sm font-semibold text-ink">
              {row.contactName ? (
                <CustomerName name={row.contactName} />
              ) : row.contactPhone ? (
                <span dir="ltr">{row.contactPhone}</span>
              ) : (
                <CustomerName name={null} />
              )}
            </span>
            <span className="shrink-0 text-xs text-ink-subtle">{when}</span>
          </span>
          {row.lastMessageText ? (
            <span className="mt-0.5 line-clamp-2 text-sm break-words text-ink-muted" data-clip="content">
              {row.lastMessageAuthor && row.lastMessageAuthor !== "customer" ? (
                <span className="text-ink-subtle">{t(MESSAGE_AUTHORS[row.lastMessageAuthor])}: </span>
              ) : null}
              <bdi>{row.lastMessageText}</bdi>
            </span>
          ) : null}
          <span className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1.5 text-xs text-ink-muted">
            {row.handoff ? (
              <Badge tone={HANDOFF_URGENCY[row.handoff.urgency].tone}>{t(HANDOFF_REASONS[row.handoff.reason])}</Badge>
            ) : null}
            {row.request ? (
              <Badge tone="accent">{t("inbox.row.request", { type: t(LEAD_TYPES[row.request.lead_type]) })}</Badge>
            ) : null}
            <span>{t(CHANNEL_LABELS[row.channel])}</span>
            {row.isAfterHours ? <AfterHoursBadge /> : null}
            {row.isSandbox ? <TestBadge /> : null}
            <Assignee row={row} member={member} />
            {row.noteCount > 0 ? (
              <span className="inline-flex items-center gap-1 text-warning">
                <IconPencil className="size-3.5" aria-hidden />
                <span aria-hidden>{row.noteCount}</span>
                <span className="sr-only">{tp("inbox.row.notes", row.noteCount)}</span>
              </span>
            ) : null}
          </span>
        </span>
      </Link>
    </li>
  );
}

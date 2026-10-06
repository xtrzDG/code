"use client";

/**
 * One conversation of the inbox, dense enough that a laptop shows ten:
 *
 *   Comfortable: the avatar; the customer with the channel and the age of
 *   the last message; then why it waits (the reason chip) and the
 *   beginning of the last message, on one line each.
 *   Compact: all of it on one line, with a small avatar.
 *
 * Who handles it, where the customer came from, after hours and the exact
 * time sit in the row's details: the hover card (RowHint) and, for screen
 * readers, inside the link. The urgency of a handoff colours the edge.
 * A row with something to resolve can be selected: its avatar turns into
 * a checkbox under the pointer, while anything is selected, and on a tap.
 */

import Link from "next/link";
import type { FocusEvent, PointerEvent } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconCheck } from "@/components/icons";
import { TestBadge } from "@/components/insights/Badges";
import { CustomerName } from "@/components/insights/common";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { conversationPath } from "@/lib/navigation";
import { formatPhone } from "@/lib/phone";

import { initialsOf } from "../../_lib/conversationModel";
import type { InboxDensity } from "../../_lib/inboxLayout";
import type { InboxRow } from "../../_lib/inboxModel";
import type { TeamMember } from "../../_lib/team";
import { ChannelGlyph, NotesMark, RowAgeText, RowDetails, RowPreview, WorkChip } from "./rowParts";

const URGENCY_EDGE = {
  critical: "before:bg-danger-solid",
  high: "before:bg-warning",
  normal: "before:bg-info",
  low: "before:bg-line-strong",
} as const;

export interface RowState {
  density: InboxDensity;
  /** The conversation open beside the list. */
  isOpen: boolean;
  /** The keyboard's cursor (j and k). */
  isCursor: boolean;
  isChecked: boolean;
  /** Something waits in it, so it can be selected and resolved. */
  isSelectable: boolean;
  /** Anything is selected: every selectable row shows its checkbox. */
  isSelecting: boolean;
  /** Being resolved right now. */
  isBusy: boolean;
}

export interface RowEvents {
  onToggle: (row: InboxRow) => void;
  /** The pointer or the focus came to the row (its details may show), or left it (null). */
  onHint: (row: InboxRow | null, element: HTMLElement | null) => void;
  onCursor: (row: InboxRow) => void;
}

function CustomerLabel({ row }: { row: InboxRow }) {
  if (row.contactName) {
    return <CustomerName name={row.contactName} />;
  }
  if (row.contactPhone) {
    return (
      <span dir="ltr" className="whitespace-nowrap">
        {formatPhone(row.contactPhone)}
      </span>
    );
  }
  return <CustomerName name={null} />;
}

/** The avatar that becomes a checkbox (Gmail-like): outside the link, over the avatar's place. */
function RowCheck({ row, state, onToggle }: { row: InboxRow; state: RowState; onToggle: () => void }) {
  const { t } = useI18n();
  const isCompact = state.density === "compact";
  const shows = state.isChecked || state.isSelecting;
  const name = row.contactName ?? (row.contactPhone ? formatPhone(row.contactPhone) : t("insights.unknownCustomer"));
  return (
    <label
      className={cn(
        "absolute z-10 flex cursor-pointer items-center justify-center rounded-full transition-opacity",
        isCompact ? "start-2 top-1/2 size-7 -translate-y-1/2" : "start-3 top-1/2 size-9 -translate-y-1/2",
        shows ? "opacity-100" : "opacity-0 group-hover/row:opacity-100 focus-within:opacity-100",
      )}
    >
      <input
        type="checkbox"
        tabIndex={-1}
        checked={state.isChecked}
        onChange={onToggle}
        aria-label={t("inboxTriage.select.row", { name })}
        className="peer sr-only"
      />
      <span
        aria-hidden
        className={cn(
          "flex size-[1.125rem] items-center justify-center rounded-[0.3rem] border bg-surface transition-colors peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-focus",
          state.isChecked ? "border-accent-solid bg-accent-solid text-on-accent" : "border-line-strong",
        )}
      >
        {state.isChecked ? <IconCheck className="size-3.5" /> : null}
      </span>
    </label>
  );
}

export function InboxRowItem({
  row,
  member,
  state,
  events,
  linkQuery,
  nowMs,
}: {
  row: InboxRow;
  /** Who handles it (null: nobody, or a former member). */
  member: TeamMember | null;
  state: RowState;
  events: RowEvents;
  linkQuery: string;
  nowMs: number;
}) {
  const { business } = useBusiness();
  const href = `${conversationPath(business.id, row.id)}${linkQuery ? `?${linkQuery}` : ""}`;
  const isCompact = state.density === "compact";
  const hideCheckAvatar = state.isSelectable && (state.isChecked || state.isSelecting);

  const hint = (event: PointerEvent<HTMLAnchorElement> | FocusEvent<HTMLAnchorElement>) => events.onHint(row, event.currentTarget);
  const leave = () => events.onHint(null, null);

  return (
    <li
      data-inbox-row={row.id}
      data-cursor={state.isCursor || undefined}
      className={cn("group/row relative", state.isBusy && "pointer-events-none opacity-50 transition-opacity")}
    >
      {state.isSelectable ? <RowCheck row={row} state={state} onToggle={() => events.onToggle(row)} /> : null}
      <Link
        href={href}
        aria-current={state.isOpen ? "page" : undefined}
        aria-busy={state.isBusy || undefined}
        onPointerEnter={(event) => event.pointerType === "mouse" && hint(event)}
        onPointerLeave={leave}
        onFocus={(event) => {
          events.onCursor(row);
          hint(event);
        }}
        onBlur={leave}
        className={cn(
          "relative flex min-w-0 transition-colors focus-visible:-outline-offset-2",
          "before:absolute before:inset-y-1.5 before:start-0 before:w-1 before:rounded-full",
          row.handoff ? URGENCY_EDGE[row.handoff.urgency] : "before:bg-transparent",
          isCompact ? "items-center gap-2 py-2 ps-11 pe-3" : "flex-col gap-0.5 py-2 ps-15 pe-4",
          state.isOpen || state.isChecked ? "bg-accent-soft" : "hover:bg-surface-muted active:bg-surface-muted",
          state.isCursor && !state.isOpen && !state.isChecked && "bg-surface-muted",
        )}
      >
        <span
          aria-hidden
          data-user-content
          className={cn(
            "absolute flex items-center justify-center rounded-full bg-surface-muted font-semibold text-ink-muted transition-opacity",
            isCompact ? "start-2 top-1/2 size-7 -translate-y-1/2 text-[0.6875rem]" : "start-3 top-1/2 size-9 -translate-y-1/2 text-[0.8125rem]",
            hideCheckAvatar ? "opacity-0" : state.isSelectable && "group-hover/row:opacity-0",
          )}
        >
          {initialsOf(row.contactName)}
        </span>

        {isCompact ? (
          <>
            <span className="w-[32%] max-w-44 shrink-0 truncate text-[0.8125rem] font-semibold text-ink">
              <CustomerLabel row={row} />
            </span>
            <WorkChip row={row} className="max-w-[34%] shrink-0" />
            <RowPreview row={row} className="flex-1 text-[0.8125rem] text-ink-muted" />
            <NotesMark count={row.noteCount} />
          </>
        ) : (
          <span className="flex min-w-0 items-baseline justify-between gap-2">
            <span className="min-w-0 truncate text-sm font-semibold text-ink">
              <CustomerLabel row={row} />
            </span>
            {row.isSandbox ? <TestBadge /> : null}
          </span>
        )}

        <span
          className={cn(
            "flex shrink-0 items-center gap-1.5 text-xs text-ink-subtle tabular-nums",
            !isCompact && "absolute end-4 top-2.5",
          )}
        >
          <ChannelGlyph channel={row.channel} />
          <RowAgeText at={row.lastMessageAt} nowMs={nowMs} />
        </span>

        {isCompact ? null : (
          <span className="flex min-w-0 items-center gap-1.5">
            <WorkChip row={row} className="max-w-[58%] shrink-0" />
            <RowPreview row={row} className="flex-1 text-sm text-ink-muted" />
            <NotesMark count={row.noteCount} />
          </span>
        )}

        <span className="sr-only">
          <RowDetails row={row} member={member} />
        </span>
      </Link>
    </li>
  );
}

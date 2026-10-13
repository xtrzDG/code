"use client";

import { morphName, SharedMorph } from "@/components/motion/SharedMorph";
import { cn } from "@/lib/cn";

import { initialsOf } from "../../_lib/conversationModel";
import type { InboxRow } from "../../_lib/inboxModel";

/**
 * The customer's initials at the start of an inbox row (where the row's
 * checkbox appears under the pointer). Opening the conversation, they fly
 * into its header (SharedMorph), as the customer's name does.
 */
export function RowAvatar({
  row,
  isCompact,
  isHidden,
  hidesOnHover,
  isOpen,
}: {
  row: InboxRow;
  isCompact: boolean;
  /** The checkbox shows in its place. */
  isHidden: boolean;
  /** The checkbox takes its place under the pointer. */
  hidesOnHover: boolean;
  /** The conversation is open: its header holds the morph's name. */
  isOpen: boolean;
}) {
  return (
    <SharedMorph name={morphName("conversation-avatar", row.id)} active={!isOpen}>
      <span
        aria-hidden
        data-user-content
        className={cn(
          "absolute flex items-center justify-center rounded-full bg-surface-muted font-semibold text-ink-muted transition-opacity",
          isCompact ? "start-2 top-1/2 size-7 -translate-y-1/2 text-[0.6875rem]" : "start-3 top-1/2 size-9 -translate-y-1/2 text-[0.8125rem]",
          isHidden ? "opacity-0" : hidesOnHover && "group-hover/row:opacity-0",
        )}
      >
        {initialsOf(row.contactName)}
      </span>
    </SharedMorph>
  );
}

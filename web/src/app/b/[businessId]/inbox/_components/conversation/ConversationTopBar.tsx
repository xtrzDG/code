"use client";

/**
 * The folded header of a conversation: back to the inbox, the customer,
 * where they wrote from, their standing ("Regular customer · 4 visits",
 * a link to their page), who of the team handles it, and the doors to the
 * notes and the details. On phones it is the bar at the top of the screen
 * (the transcript comes right under it); everything else about the
 * conversation waits behind "Details". Its avatar and name are where the
 * inbox row's fly to when the conversation opens (a view transition).
 */

import Link from "next/link";
import type { ReactNode } from "react";

import { CustomerStandingLink } from "@/components/customers/CustomerStandingLink";
import { IconArrowLeft, IconInfo, IconPencil } from "@/components/icons";
import { CHANNEL_LABELS, CONVERSATION_STATUS } from "@/components/insights/labels";
import { morphName, SharedMorph } from "@/components/motion/SharedMorph";
import type { ConversationSummaryView } from "@/components/insights/types";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { languageName } from "@/lib/format";
import { formatPhone } from "@/lib/phone";

import { initialsOf } from "../../_lib/conversationModel";

const ICON_BUTTON =
  "motion-press relative flex size-10 shrink-0 cursor-pointer items-center justify-center rounded-full border border-line bg-surface text-ink-muted hover:border-line-strong hover:text-ink";

export function ConversationTopBar({
  businessId,
  conversation,
  backHref,
  assignMenu,
  noteCount,
  onNotes,
  onDetails,
  showPanelButtons,
}: {
  businessId: string;
  conversation: ConversationSummaryView;
  backHref: string;
  /** The assign menu (null for test conversations: they are not team work). */
  assignMenu: ReactNode;
  noteCount: number | null;
  onNotes: () => void;
  onDetails: () => void;
  /** False when the panel is a column of its own (wide screens). */
  showPanelButtons: boolean;
}) {
  const { t, tp, locale } = useI18n();
  const phone = conversation.contact_phone_number ? formatPhone(conversation.contact_phone_number) : null;
  const name = conversation.contact_name ?? phone ?? t("insights.unknownCustomer");
  const subline = [
    t(CHANNEL_LABELS[conversation.channel]),
    conversation.language ? languageName(conversation.language, locale) : null,
    t(CONVERSATION_STATUS[conversation.status].label),
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <header
      className={cn(
        "sticky top-0 z-20 -mx-4 -mt-6 flex items-center gap-2 border-b border-line bg-canvas/85 px-3 pt-[calc(0.5rem+env(safe-area-inset-top))] pb-2 backdrop-blur-xl sm:-mx-6 sm:px-5",
        "lg:static lg:mx-0 lg:mt-0 lg:rounded-t-2xl lg:border lg:bg-surface lg:px-4 lg:py-3 lg:backdrop-blur-none",
      )}
    >
      <Link href={backHref} aria-label={t("inboxCard.back")} className={cn(ICON_BUTTON, "border-transparent bg-transparent lg:hidden")}>
        <IconArrowLeft className="size-5 rtl:-scale-x-100" aria-hidden />
      </Link>
      <SharedMorph name={morphName("conversation-avatar", conversation.id)}>
        <span
          aria-hidden
          data-user-content
          className="hidden size-10 shrink-0 items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-accent-ink sm:flex"
        >
          {initialsOf(conversation.contact_name)}
        </span>
      </SharedMorph>
      {/* Room for the name, the subline and the customer's standing (which arrives later): the header keeps its height. */}
      <div className="min-h-15 min-w-0 flex-1 leading-tight">
        {/* The name keeps its own direction (<bdi>) but sits at the start, next to the avatar, in any script. */}
        {/* The inbox row's customer flies into this place when the conversation opens (SharedMorph). */}
        <SharedMorph name={morphName("conversation-name", conversation.id)}>
          <h2 id="conversation-title" className="truncate text-start text-base font-semibold text-ink">
            <bdi dir={conversation.contact_name ? "auto" : "ltr"} data-user-content={conversation.contact_name ? true : undefined}>
              {name}
            </bdi>
          </h2>
        </SharedMorph>
        <p className="truncate text-xs text-ink-subtle">{subline}</p>
        {conversation.is_sandbox ? null : <CustomerStandingLink businessId={businessId} contactId={conversation.contact_id} />}
      </div>
      {assignMenu}
      {showPanelButtons ? (
        <>
          <button
            type="button"
            onClick={onNotes}
            aria-haspopup="dialog"
            aria-label={noteCount ? tp("inboxCard.openNotesCount", noteCount) : t("inboxCard.openNotes")}
            className={ICON_BUTTON}
          >
            <IconPencil className="size-[1.125rem]" aria-hidden />
            {noteCount ? (
              <span
                aria-hidden
                className="absolute -end-1 -top-1 min-w-5 rounded-full bg-warning px-1 text-center text-[0.6875rem] leading-5 font-semibold text-canvas"
              >
                {noteCount}
              </span>
            ) : null}
          </button>
          <button
            type="button"
            onClick={onDetails}
            aria-haspopup="dialog"
            aria-label={t("inboxCard.openDetailsOf", { name })}
            className={ICON_BUTTON}
          >
            <IconInfo className="size-[1.125rem]" aria-hidden />
          </button>
        </>
      ) : null}
    </header>
  );
}

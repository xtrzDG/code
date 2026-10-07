"use client";

/**
 * The list of quick replies above the reply box (a listbox the text field
 * controls: arrows move, Enter inserts, Escape closes). Each shows its
 * shortcut, its name and the text as it will go out, filled in for this
 * conversation; what could not be filled is named, to be completed after
 * inserting.
 */

import Link from "next/link";

import { useBusiness } from "@/components/business/BusinessContext";
import { Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { businessPath } from "@/lib/navigation";

import type { FilledQuickReplyView } from "../../_lib/types";
import type { QuickReplyPicker as Picker } from "../../_lib/useQuickReplyPicker";

export function QuickReplyPicker({
  listId,
  picker,
  onPick,
}: {
  listId: string;
  picker: Picker;
  onPick: (reply: FilledQuickReplyView) => void;
}) {
  const { t } = useI18n();
  const { business, isOwner } = useBusiness();
  if (!picker.isOpen) {
    return null;
  }
  const isLoading = picker.replies.data === undefined && !picker.replies.error;
  const isEmpty = (picker.replies.data?.items ?? []).length === 0;

  return (
    <div className="animate-settle absolute inset-x-0 bottom-full z-20 mb-2 overflow-hidden rounded-2xl border border-line bg-surface shadow-2xl">
      <p className="flex items-center justify-between gap-3 border-b border-line px-4 py-2 text-xs font-medium text-ink-subtle">
        <span>{t("inboxCard.quickReplies.listLabel")}</span>
        {isOwner ? (
          <Link href={businessPath(business.id, "settings/quick-replies")} className="text-accent hover:underline">
            {t("inboxCard.quickReplies.manage")}
          </Link>
        ) : null}
      </p>
      {isLoading ? (
        <p className="flex items-center gap-2 px-4 py-3 text-sm text-ink-muted" role="status">
          <Spinner size="sm" />
          {t("inboxCard.quickReplies.loading")}
        </p>
      ) : isEmpty ? (
        <div className="space-y-1 px-4 py-3 text-sm">
          <p className="text-ink">{t("inboxCard.quickReplies.empty")}</p>
          {isOwner ? <p className="text-ink-muted">{t("inboxCard.quickReplies.emptyOwner")}</p> : null}
        </div>
      ) : picker.matches.length === 0 ? (
        <p className="px-4 py-3 text-sm text-ink-muted">{t("inboxCard.quickReplies.noMatch", { query: picker.query })}</p>
      ) : null}
      <ul
        id={listId}
        role="listbox"
        aria-label={t("inboxCard.quickReplies.listLabel")}
        className={cn("max-h-64 overflow-y-auto py-1", picker.matches.length === 0 && "hidden")}
      >
        {picker.matches.map((reply, index) => {
          const isActive = index === picker.activeIndex;
          return (
            <li
              key={reply.id}
              id={`${listId}-${reply.id}`}
              role="option"
              aria-selected={isActive}
              onMouseEnter={() => picker.setActiveIndex(index)}
              // Keep the focus in the text field: the click picks, the field keeps typing.
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => onPick(reply)}
              className={cn("cursor-pointer px-4 py-2.5 text-sm", isActive ? "bg-accent-soft" : "hover:bg-surface-muted")}
            >
              <span className="flex items-baseline gap-2">
                <span className="font-mono text-xs text-accent-ink" dir="auto" data-user-content>
                  /{reply.shortcut}
                </span>
                <span className="min-w-0 truncate font-medium text-ink" dir="auto" data-user-content>
                  {reply.title}
                </span>
              </span>
              <span className="mt-0.5 line-clamp-2 text-ink-muted" dir="auto" data-user-content>
                {reply.text}
              </span>
              {(reply.missing_variables ?? []).length > 0 ? (
                <span className="mt-1 block text-xs text-warning">
                  {t("inboxCard.quickReplies.missing")}{" "}
                  {(reply.missing_variables ?? []).map((variable) => t(`inboxCard.quickReplies.variables.${variable}`)).join(", ")}
                </span>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

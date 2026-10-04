"use client";

import { IconPencil } from "@/components/icons";
import type { MessageView } from "@/components/insights/types";
import { GuardChip } from "@/components/teaching/GuardChip";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

/**
 * Under an answer of the assistant: the reply guard's verdict, if it did
 * anything, and for owners "Fix answer", which opens the correction dialog
 * on this answer.
 */
export function AnswerTools({
  message,
  onFix,
  alignEnd,
}: {
  message: MessageView;
  onFix: ((messageId: string) => void) | null;
  alignEnd: boolean;
}) {
  const { t } = useI18n();
  const hasGuard = Boolean(message.guard?.verdict && message.guard.verdict !== "clean");
  if (!hasGuard && !onFix) {
    return null;
  }
  return (
    <div className={cn("mt-1.5 flex flex-wrap items-center gap-2", alignEnd && "justify-end")}>
      <GuardChip guard={message.guard} />
      {onFix ? (
        <button
          type="button"
          onClick={() => onFix(message.id)}
          aria-label={t("teaching.fix.actionLabel")}
          data-fix-answer=""
          className="inline-flex min-h-8 items-center gap-1 rounded-full px-2.5 text-xs font-medium text-accent-ink hover:bg-accent-soft focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        >
          <IconPencil className="size-3.5" aria-hidden />
          {t("teaching.fix.action")}
        </button>
      ) : null}
    </div>
  );
}

"use client";

import type { ConversationRating } from "@/components/insights/types";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

const OPTIONS: { value: ConversationRating; label: "conversations.rating.good" | "conversations.rating.bad"; mark: string }[] = [
  { value: "good", label: "conversations.rating.good", mark: "▲" },
  { value: "bad", label: "conversations.rating.bad", mark: "▼" },
];

/**
 * Good / bad verdict on how the assistant handled the conversation (concept
 * section 8), for the weekly quality review. Pressing the chosen one again
 * clears it. The choice shows at once; a refusal puts the old one back.
 */
export function RatingControl({
  value,
  isPending,
  onChange,
}: {
  value: ConversationRating | null;
  isPending: boolean;
  onChange: (rating: ConversationRating | null) => void;
}) {
  const { t } = useI18n();
  return (
    <div role="group" aria-label={t("conversations.rating.label")} className="flex items-center gap-2">
      <span className="text-xs text-ink-muted">{t("conversations.rating.label")}</span>
      <div className="inline-flex rounded-xl border border-line bg-surface-muted p-0.5">
        {OPTIONS.map((option) => {
          const isActive = value === option.value;
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={isActive}
              aria-busy={isPending || undefined}
              onClick={() => onChange(isActive ? null : option.value)}
              className={cn(
                "inline-flex min-h-9 items-center gap-1.5 rounded-lg px-3 text-sm font-medium transition-colors",
                isActive
                  ? option.value === "good"
                    ? "bg-success-soft text-success"
                    : "bg-danger-soft text-danger"
                  : "text-ink-muted hover:text-ink",
              )}
            >
              <span aria-hidden>{option.mark}</span>
              {t(option.label)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

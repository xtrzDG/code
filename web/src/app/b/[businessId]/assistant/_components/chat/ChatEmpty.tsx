"use client";

import { IconChat } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

const SUGGESTIONS: readonly MessageKey[] = [
  "assistant.chat.suggestions.hours",
  "assistant.chat.suggestions.price",
  "assistant.chat.suggestions.booking",
  "assistant.chat.suggestions.human",
];

/** An empty conversation: what to try first, as one-click messages. */
export function ChatEmpty({ onSuggest }: { onSuggest: (message: string) => void }) {
  const { t } = useI18n();
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
      <div className="flex size-12 items-center justify-center rounded-full bg-accent-soft text-accent" aria-hidden>
        <IconChat className="size-6" />
      </div>
      <div className="space-y-1">
        <p className="font-medium text-ink">{t("assistant.chat.emptyTitle")}</p>
        <p className="max-w-md text-sm text-ink-muted">{t("assistant.chat.emptyDescription")}</p>
      </div>
      <div className="flex max-w-xl flex-wrap justify-center gap-2">
        {SUGGESTIONS.map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => onSuggest(t(key))}
            className="rounded-full border border-line-strong bg-surface px-3 py-1.5 text-sm text-ink hover:bg-surface-muted focus-visible:outline-2 focus-visible:outline-focus"
          >
            {t(key)}
          </button>
        ))}
      </div>
    </div>
  );
}

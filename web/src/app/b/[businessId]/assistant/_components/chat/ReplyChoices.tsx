"use client";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

/**
 * The options an answer offered, under it. While the answer is the last
 * one they are buttons: a tap sends the label as the customer's message,
 * as a tap on a Telegram or WhatsApp button does. Afterwards they stay as
 * a record of what was offered.
 */
export function ReplyChoices({
  choices,
  onChoose,
  isSending,
}: {
  choices: readonly string[];
  onChoose: ((label: string) => void) | null;
  isSending: boolean;
}) {
  const { t } = useI18n();
  const chip = "rounded-full border px-3 py-1.5 text-sm font-medium";

  if (onChoose === null) {
    return (
      <ul className="flex max-w-[85%] flex-wrap gap-1.5" aria-label={t("assistant.chat.choicesLabel")}>
        {choices.map((choice) => (
          <li key={choice} dir="auto" data-user-content className={cn(chip, "border-line bg-surface text-ink-muted")}>
            {choice}
          </li>
        ))}
      </ul>
    );
  }
  return (
    <div role="group" aria-label={t("assistant.chat.choicesLabel")} className="flex max-w-[85%] flex-wrap gap-2" data-reply-choices="">
      {choices.map((choice) => (
        <button
          key={choice}
          type="button"
          dir="auto"
          data-user-content
          disabled={isSending}
          onClick={() => onChoose(choice)}
          className={cn(
            chip,
            "border-accent/40 bg-surface text-accent hover:bg-accent-soft focus-visible:outline-2 focus-visible:outline-focus disabled:opacity-60",
          )}
        >
          {choice}
        </button>
      ))}
    </div>
  );
}

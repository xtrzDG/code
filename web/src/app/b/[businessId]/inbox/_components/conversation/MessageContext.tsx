"use client";

/**
 * Two small lines around a bubble of the transcript. Above a customer's
 * message: what it refers to when the platform said so ("Reply to your
 * story" on Instagram). Under an answer of the assistant: the options it
 * offered to tap, as the customer saw them (buttons, a list or quick
 * replies; a numbered list where the channel has none). The options here
 * are a record, not buttons: the team does not tap for the customer.
 */

import { IconImage, IconList } from "@/components/icons";
import type { MessageView } from "@/components/insights/types";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

export function StoryContextLine({
  note,
  alignEnd,
}: {
  note: NonNullable<MessageView["context_note"]>;
  alignEnd: boolean;
}) {
  const { t } = useI18n();
  return (
    <p
      className={cn("mb-1 flex items-center gap-1 text-xs text-ink-muted", alignEnd && "justify-end")}
      data-message-context={note}
    >
      <IconImage className="size-3.5 shrink-0" aria-hidden />
      {t(`inboxCard.messageContext.${note}`)}
    </p>
  );
}

export function OfferedChoices({ choices, alignEnd }: { choices: readonly string[]; alignEnd: boolean }) {
  const { t } = useI18n();
  const label = t("inboxCard.offeredChoices");
  return (
    <div className={cn("mt-1.5 flex flex-wrap items-center gap-1.5", alignEnd && "justify-end")} data-offered-choices="">
      <span className="inline-flex items-center gap-1 text-xs text-ink-subtle">
        <IconList className="size-3.5" aria-hidden />
        {label}
      </span>
      <ul className="contents" aria-label={label}>
        {choices.map((choice) => (
          <li
            key={choice}
            dir="auto"
            data-user-content
            className="rounded-full border border-accent/40 bg-surface px-2.5 py-0.5 text-xs font-medium text-accent"
          >
            {choice}
          </li>
        ))}
      </ul>
    </div>
  );
}

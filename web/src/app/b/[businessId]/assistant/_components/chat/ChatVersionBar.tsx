"use client";

import { IconInfo, IconRefresh } from "@/components/icons";
import { Button, Field, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { ChatChoice, ChatTarget } from "@/lib/assistant/chatTargets";

const NOTES = {
  live: "updates.chat.noteLive",
  changes: "updates.chat.noteChanges",
  history: "updates.chat.noteHistory",
} as const;

/**
 * Who the chat talks to — "What customers get now" or "With your changes"
 * (an update opened from History only when it was opened from there) —
 * a fresh conversation, and what a test conversation does not do.
 */
export function ChatVersionBar({
  choices,
  target,
  isSending,
  onStartNew,
}: {
  choices: readonly ChatChoice[];
  target: ChatTarget;
  isSending: boolean;
  onStartNew: (target?: ChatTarget) => void;
}) {
  const { t } = useI18n();
  const label = (choice: ChatChoice) =>
    choice.target === "history" ? t("updates.chat.history", { number: choice.versionNumber ?? "" }) : t(`updates.chat.${choice.target}`);
  return (
    <>
      <div className="flex flex-col gap-3 border-b border-line px-4 py-4 sm:flex-row sm:items-end sm:justify-between sm:px-6">
        <Field label={t("updates.chat.target")} className="sm:w-80">
          {(control) => (
            <Select
              {...control}
              value={target}
              disabled={isSending}
              onChange={(event) => onStartNew(event.target.value as ChatTarget)}
            >
              {choices.map((choice) => (
                <option key={choice.target} value={choice.target}>
                  {label(choice)}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Button variant="secondary" leadingIcon={<IconRefresh className="size-4" aria-hidden />} onClick={() => onStartNew()} disabled={isSending}>
          {t("assistant.chat.newConversation")}
        </Button>
      </div>
      <p className="flex items-start gap-2 border-b border-line bg-surface-muted/50 px-4 py-2.5 text-sm text-ink-muted sm:px-6">
        <IconInfo className="mt-0.5 size-4 shrink-0" aria-hidden />
        {t(NOTES[target])}
      </p>
    </>
  );
}

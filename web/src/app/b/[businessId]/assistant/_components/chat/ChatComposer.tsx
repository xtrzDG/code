"use client";

import { useId, type FormEvent, type KeyboardEvent, type RefObject } from "react";

import { IconSend } from "@/components/icons";
import { Button, Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";

const MAX_MESSAGE_LENGTH = 2000;

/** The message box: Enter sends, Shift+Enter starts a new line. */
export function ChatComposer({
  input,
  text,
  isSending,
  onChange,
  onSubmit,
  onKeyDown,
}: {
  input: RefObject<HTMLTextAreaElement | null>;
  text: string;
  isSending: boolean;
  onChange: (text: string) => void;
  onSubmit: (event?: FormEvent) => void;
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
}) {
  const { t, tp } = useI18n();
  const formId = useId();
  return (
    <>
      <form id={formId} onSubmit={onSubmit} className="flex items-end gap-2 border-t border-line px-4 py-3 sm:px-6">
        <label htmlFor={`${formId}-text`} className="sr-only">
          {t("assistant.chat.inputLabel")}
        </label>
        <Textarea
          ref={input}
          id={`${formId}-text`}
          rows={2}
          dir="auto"
          value={text}
          maxLength={MAX_MESSAGE_LENGTH}
          placeholder={t("assistant.chat.placeholder")}
          aria-describedby={`${formId}-hint`}
          className="min-h-11 resize-none"
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={onKeyDown}
        />
        <Button
          type="submit"
          aria-label={t("assistant.chat.send")}
          disabled={text.trim() === "" || isSending}
          className="h-11"
          leadingIcon={<IconSend className="size-4" aria-hidden />}
        >
          <span className="sr-only sm:not-sr-only">{t("assistant.chat.send")}</span>
        </Button>
      </form>
      <p id={`${formId}-hint`} className="px-4 pb-3 text-xs text-ink-subtle sm:px-6">
        {tp("assistant.chat.inputHint", MAX_MESSAGE_LENGTH)}
      </p>
    </>
  );
}

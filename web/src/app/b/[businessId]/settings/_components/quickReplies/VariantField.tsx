"use client";

/**
 * The text of a quick reply in one language: a text box, buttons that
 * insert the variables the API fills in ({name}, {booking_time},
 * {business_name}) where the caret is, and how a customer would read it.
 */

import { useId, useRef } from "react";

import { Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { languageName } from "@/lib/format";
import {
  insertAt,
  placeholderOf,
  previewQuickReply,
  QUICK_REPLY_TEXT_MAX_LENGTH,
  QUICK_REPLY_VARIABLES,
} from "@/lib/quickReplies";

export function VariantField({
  language,
  value,
  businessName,
  onChange,
}: {
  language: string;
  value: string;
  businessName: string;
  onChange: (text: string) => void;
}) {
  const { t, locale } = useI18n();
  const id = useId();
  const textRef = useRef<HTMLTextAreaElement>(null);
  const languageLabel = languageName(language, locale);
  const tooLong = value.length > QUICK_REPLY_TEXT_MAX_LENGTH;
  const preview = previewQuickReply(value, {
    name: t("quickReplies.editor.sample.name"),
    booking_time: t("quickReplies.editor.sample.bookingTime"),
    business_name: businessName,
  });

  const insert = (variable: (typeof QUICK_REPLY_VARIABLES)[number]) => {
    const element = textRef.current;
    const start = element?.selectionStart ?? value.length;
    const end = element?.selectionEnd ?? value.length;
    const next = insertAt(value, placeholderOf(variable), start, end);
    onChange(next.text);
    requestAnimationFrame(() => {
      element?.focus();
      element?.setSelectionRange(next.caret, next.caret);
    });
  };

  return (
    <div className="space-y-2 rounded-2xl border border-line bg-surface p-3.5">
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor={`${id}-text`} className="text-sm font-medium text-ink">
          {t("quickReplies.editor.textIn", { language: languageLabel })}
        </label>
        <span className={cn("text-xs tabular-nums", tooLong ? "text-danger" : "text-ink-subtle")}>
          {t("quickReplies.editor.length", { count: value.length, max: QUICK_REPLY_TEXT_MAX_LENGTH })}
        </span>
      </div>
      <Textarea
        ref={textRef}
        id={`${id}-text`}
        lang={language}
        rows={3}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={tooLong || undefined}
      />
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-xs text-ink-subtle">{t("quickReplies.editor.insert")}:</span>
        {QUICK_REPLY_VARIABLES.map((variable) => (
          <button
            key={variable}
            type="button"
            onClick={() => insert(variable)}
            aria-label={t("quickReplies.editor.insertLabel", {
              variable: t(`quickReplies.variables.${variable}`),
              language: languageLabel,
            })}
            className="motion-press cursor-pointer rounded-full border border-line bg-surface-muted px-2.5 py-1 text-xs text-ink-muted hover:border-accent/40 hover:text-accent-ink"
          >
            {t(`quickReplies.variables.${variable}`)}
          </button>
        ))}
      </div>
      {value.trim() ? (
        <figure className="rounded-xl bg-surface-muted px-3 py-2">
          <figcaption className="text-xs text-ink-subtle">{t("quickReplies.editor.preview")}</figcaption>
          <p dir="auto" lang={language} data-user-content className="mt-0.5 text-sm break-words whitespace-pre-wrap text-ink">
            {preview}
          </p>
        </figure>
      ) : null}
    </div>
  );
}

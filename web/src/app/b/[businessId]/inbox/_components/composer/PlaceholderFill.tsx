"use client";

/**
 * What a quick reply could not fill in by itself ({name} before the
 * customer gave one, {booking_time} without an upcoming booking): one small
 * field per part, which puts the value into the text. Sending waits until
 * no part in braces is left.
 */

import { useId, useState, type FormEvent } from "react";

import { Button, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { fillPlaceholder, type QuickReplyVariable } from "@/lib/quickReplies";

function VariableField({ variable, onFill }: { variable: QuickReplyVariable; onFill: (value: string) => void }) {
  const { t } = useI18n();
  const id = useId();
  const [value, setValue] = useState("");
  const label = t(`inboxCard.quickReplies.variables.${variable}`);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (value.trim()) {
      onFill(value);
      setValue("");
    }
  };

  return (
    <form onSubmit={submit} className="flex min-w-0 items-center gap-2">
      <label htmlFor={id} className="sr-only">
        {t("inboxCard.quickReplies.fillLabel", { variable: label })}
      </label>
      <Input
        id={id}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder={label}
        className="h-8 min-w-0 flex-1 text-sm"
        autoComplete="off"
      />
      <Button type="submit" size="sm" variant="secondary" disabled={!value.trim()}>
        {t("inboxCard.quickReplies.fill")}
      </Button>
    </form>
  );
}

export function PlaceholderFill({
  draft,
  placeholders,
  onDraft,
}: {
  draft: string;
  placeholders: readonly QuickReplyVariable[];
  onDraft: (text: string) => void;
}) {
  const { t } = useI18n();
  if (placeholders.length === 0) {
    return null;
  }
  return (
    <div className="mb-2 space-y-2 rounded-xl border border-warning/30 bg-warning-soft px-3 py-2.5">
      <p className="text-xs font-medium text-warning">
        {t("inboxCard.quickReplies.placeholdersLeft", {
          variables: placeholders.map((variable) => t(`inboxCard.quickReplies.variables.${variable}`)).join(", "),
        })}
      </p>
      {placeholders.map((variable) => (
        <VariableField key={variable} variable={variable} onFill={(value) => onDraft(fillPlaceholder(draft, variable, value))} />
      ))}
    </div>
  );
}

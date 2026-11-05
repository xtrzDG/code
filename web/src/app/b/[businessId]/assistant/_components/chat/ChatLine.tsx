"use client";

import { describeError } from "@/api/errors";
import { IconAlert } from "@/components/icons";
import { Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import type { ChatEntry } from "../../_lib/chatEntries";
import { AssistantLine } from "./AssistantLine";

/** One line of the test chat: the customer's message (with retry), a silence, a note or an answer. */
export function ChatLine({
  entry,
  answerLabel,
  onRetry,
  onChoose,
  isSending,
}: {
  entry: ChatEntry;
  answerLabel: (versionId: string | null, number?: number | null) => string;
  onRetry: (message: string, key: string) => void;
  /** Only for the last answer: a tap on one of its options. */
  onChoose?: ((label: string) => void) | null;
  isSending: boolean;
}) {
  const { t } = useI18n();

  if (entry.kind === "customer") {
    const failure = entry.error ? describeError(entry.error, t, { external_service_error: "assistant.chat.errors.service" }) : null;
    return (
      <div className="flex flex-col items-end gap-1">
        <p className="mb-0.5 text-xs font-medium text-ink-subtle">{t("assistant.authors.customer")}</p>
        <div
          className={cn(
            "max-w-[85%] rounded-2xl rounded-ee-md bg-accent-solid px-4 py-2.5 text-sm break-words whitespace-pre-wrap text-on-accent",
            entry.status === "sending" && "opacity-70",
            entry.status === "failed" && "bg-danger-soft text-ink ring-1 ring-danger/30",
          )}
          dir="auto"
          data-user-content
        >
          {entry.text}
        </div>
        {entry.status === "failed" && failure ? (
          <div role="alert" className="flex max-w-[85%] flex-wrap items-center justify-end gap-2 text-sm text-danger">
            <IconAlert className="size-4 shrink-0" aria-hidden />
            <span>
              {t("assistant.chat.failed")} {failure.title}
              {failure.detail ? ` ${failure.detail}` : ""}
              {failure.requestId ? ` ${t("common.requestId", { id: failure.requestId })}` : ""}
            </span>
            <Button size="sm" variant="secondary" disabled={isSending} onClick={() => onRetry(entry.text, entry.key)}>
              {t("common.retry")}
            </Button>
          </div>
        ) : null}
      </div>
    );
  }

  if (entry.kind === "silent") {
    return <p className="mx-auto max-w-md text-center text-sm text-ink-muted">{t("assistant.chat.silent")}</p>;
  }

  if (entry.kind === "note") {
    return (
      <div className="mx-auto max-w-[85%] rounded-xl bg-warning-soft px-4 py-2 text-sm text-ink-muted">
        <span className="mb-0.5 block text-xs font-medium">{t(`assistant.authors.${entry.author}`)}</span>
        <span dir="auto" data-user-content className="break-words whitespace-pre-wrap">
          {entry.text}
        </span>
      </div>
    );
  }

  return <AssistantLine entry={entry} answerLabel={answerLabel} onChoose={onChoose} isSending={isSending} />;
}

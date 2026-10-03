"use client";

/**
 * The messages with the customer as chat bubbles, split by day; a long
 * conversation starts with its newest messages and a button above them
 * loads the earlier ones. What the assistant did is said in plain words
 * under its message ("Checked free time"); the requests behind it, the
 * model and the cost are in "Technical details". Internal notes of the
 * team are never here: this is what the customer and the assistant said.
 */

import { describeError } from "@/api/errors";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconCheck, IconAlert } from "@/components/icons";
import { formatLocalDate } from "@/components/insights/dates";
import { MESSAGE_AUTHORS, TOOL_LABELS } from "@/components/insights/labels";
import type { MessageView } from "@/components/insights/types";
import { Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { groupMessagesByDay, messageSide } from "../../_lib/conversationModel";
import type { EarlierMessages } from "../../_lib/useEarlierMessages";
import { hasTechnicalDetails, MessageTechnicalDetails } from "./TechnicalDetails";

const BUBBLE: Record<MessageView["author"], string> = {
  customer: "rounded-bl-md bg-surface-muted text-ink",
  assistant: "rounded-br-md bg-accent-soft text-ink",
  staff: "rounded-br-md bg-success-soft text-ink",
  system: "bg-transparent text-ink-muted italic",
};

export function Transcript({
  messages,
  earlier,
  label,
}: {
  messages: readonly MessageView[];
  earlier?: EarlierMessages;
  label: string;
}) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();

  if (messages.length === 0 && !earlier?.hasMore) {
    return <p className="py-8 text-center text-sm text-ink-muted">{t("conversations.emptyTranscript")}</p>;
  }

  return (
    <section aria-label={label} className="space-y-6" data-transcript>
      {earlier?.hasMore ? (
        <div className="flex flex-col items-center gap-2">
          {earlier.error ? (
            <p className="text-xs text-danger" role="alert">
              {describeError(earlier.error, t).title}
            </p>
          ) : null}
          <Button
            variant="secondary"
            size="sm"
            onClick={earlier.load}
            isLoading={earlier.isLoading}
            loadingText={t("conversations.earlierLoading")}
          >
            {earlier.error ? t("common.retry") : t("conversations.earlierMessages")}
          </Button>
        </div>
      ) : null}
      {groupMessagesByDay(messages, business.timezone).map((day) => (
        <section key={day.date} aria-label={formatLocalDate(day.date, locale, { dateStyle: "full" })}>
          <p
            className="sticky top-16 z-[1] mx-auto mb-4 w-fit rounded-full border border-line bg-surface/90 px-3 py-1 text-xs font-medium text-ink-subtle backdrop-blur lg:top-2"
            aria-hidden
          >
            {formatLocalDate(day.date, locale, { dateStyle: "full" })}
          </p>
          <ol className="space-y-4">
            {day.messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </ol>
        </section>
      ))}
    </section>
  );
}

function memberName(
  member: { display_name?: string | null; email?: string | null; phone_number?: string | null } | undefined,
): string | null {
  return member ? (member.display_name ?? member.email ?? member.phone_number ?? null) : null;
}

function MessageBubble({ message }: { message: MessageView }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const { business, me, isPlatformAdmin } = useBusiness();
  const side = messageSide(message.author);
  // A system note with tool calls is an action of the voice agent during a
  // call ("Voice agent called check_availability."): the actions below say
  // it in the interface language, so the note itself is not shown.
  const isVoiceAction = message.author === "system" && (message.tool_calls?.length ?? 0) > 0;
  const sender = message.sent_by
    ? message.sent_by === me.user.id
      ? t("conversations.author.you")
      : memberName(business.members.find((member) => member.user_id === message.sent_by))
    : null;
  const calls = message.tool_calls ?? [];

  return (
    <li className={cn("flex", side === "end" ? "justify-end" : side === "center" ? "justify-center" : "justify-start")}>
      <div
        className={cn(
          "min-w-0",
          side === "center" ? "max-w-full text-center" : "max-w-[88%] sm:max-w-[75%]",
          isVoiceAction && "w-full sm:w-[75%]",
        )}
      >
        <p className={cn("mb-1 text-xs text-ink-subtle", side === "end" && "text-right")}>
          <span className="font-medium text-ink-muted">
            {isVoiceAction ? t("conversations.author.voiceAgent") : t(MESSAGE_AUTHORS[message.author])}
          </span>
          {sender ? (
            <>
              {" · "}
              <span dir="auto">{sender}</span>
            </>
          ) : null}
          {" · "}
          <time dateTime={new Date(message.created_at / 1000).toISOString()}>{format.time(message.created_at)}</time>
        </p>
        {isVoiceAction ? null : (
          <div
            dir="auto"
            className={cn("rounded-2xl px-4 py-2.5 text-[0.9375rem] leading-6 break-words whitespace-pre-wrap", BUBBLE[message.author])}
          >
            {message.text}
          </div>
        )}
        {calls.length > 0 ? (
          <ul className={cn("mt-1.5 flex flex-wrap gap-1.5", side === "end" && "justify-end")} aria-label={t("inboxCard.actions.label")}>
            {calls.map((call, index) => (
              <li
                key={index}
                className={cn(
                  "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs",
                  call.is_error ? "bg-danger-soft text-danger" : "bg-surface-muted text-ink-muted",
                )}
              >
                {call.is_error ? <IconAlert className="size-3.5" aria-hidden /> : <IconCheck className="size-3.5" aria-hidden />}
                {t(TOOL_LABELS[call.tool_name])}
                {call.is_error ? <span className="sr-only">: {t("conversations.toolError")}</span> : null}
              </li>
            ))}
          </ul>
        ) : null}
        {hasTechnicalDetails(message, isPlatformAdmin) ? <MessageTechnicalDetails message={message} className="mt-1.5" /> : null}
      </div>
    </li>
  );
}

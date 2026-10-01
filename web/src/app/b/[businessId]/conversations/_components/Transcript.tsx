"use client";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconChevronRight } from "@/components/icons";
import { formatLocalDate } from "@/components/insights/dates";
import { MESSAGE_AUTHORS, TOOL_LABELS } from "@/components/insights/labels";
import { formatMicroUsd } from "@/components/insights/numbers";
import type { MessageView, ToolCallView } from "@/components/insights/types";
import { Badge } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { groupMessagesByDay, messageSide, prettyJson } from "./conversationModel";

const BUBBLE: Record<MessageView["author"], string> = {
  customer: "rounded-bl-md bg-surface-muted text-ink",
  assistant: "rounded-br-md bg-accent-soft text-ink",
  staff: "rounded-br-md bg-success-soft text-ink",
  system: "bg-transparent text-ink-muted italic",
};

/** The messages of a conversation as chat bubbles, split by day, with the assistant's actions. */
export function Transcript({ messages }: { messages: readonly MessageView[] }) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();

  if (messages.length === 0) {
    return <p className="py-8 text-center text-sm text-ink-muted">{t("conversations.emptyTranscript")}</p>;
  }

  return (
    <div className="space-y-6">
      {groupMessagesByDay(messages, business.timezone).map((day) => (
        <section key={day.date} aria-label={formatLocalDate(day.date, locale, { dateStyle: "full" })}>
          <p className="mb-4 flex items-center gap-3 text-xs font-medium text-ink-subtle" aria-hidden>
            <span className="h-px flex-1 bg-line" />
            {formatLocalDate(day.date, locale, { dateStyle: "full" })}
            <span className="h-px flex-1 bg-line" />
          </p>
          <ol className="space-y-4">
            {day.messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}

function MessageBubble({ message }: { message: MessageView }) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const { business, me } = useBusiness();
  const side = messageSide(message.author);
  const tokens = message.input_tokens + message.output_tokens;
  const sender = message.sent_by
    ? message.sent_by === me.user.id
      ? t("conversations.author.you")
      : memberName(business.members.find((member) => member.user_id === message.sent_by))
    : null;

  return (
    <li className={cn("flex", side === "end" ? "justify-end" : side === "center" ? "justify-center" : "justify-start")}>
      <div className={cn("min-w-0", side === "center" ? "max-w-full text-center" : "max-w-[88%] sm:max-w-[75%]")}>
        <p className={cn("mb-1 text-xs text-ink-subtle", side === "end" && "text-right")}>
          <span className="font-medium text-ink-muted">{t(MESSAGE_AUTHORS[message.author])}</span>
          {sender ? (
            <>
              {" · "}
              <span dir="auto">{sender}</span>
            </>
          ) : null}
          {" · "}
          <time dateTime={new Date(message.created_at / 1000).toISOString()}>{format.time(message.created_at)}</time>
        </p>
        <div
          dir="auto"
          className={cn("rounded-2xl px-4 py-2.5 text-sm break-words whitespace-pre-wrap", BUBBLE[message.author])}
        >
          {message.text}
        </div>
        {message.tool_calls && message.tool_calls.length > 0 ? <ToolCalls calls={message.tool_calls} /> : null}
        {tokens > 0 ? (
          <p className={cn("mt-1 text-xs text-ink-subtle", side === "end" && "text-right")}>
            {[
              message.model_id,
              t("conversations.messageTokens", { count: format.number(tokens) }),
              formatMicroUsd(message.cost_micro_usd, locale),
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
        ) : null}
      </div>
    </li>
  );
}

function ToolCalls({ calls }: { calls: readonly ToolCallView[] }) {
  const { t, tp } = useI18n();
  const failed = calls.some((call) => call.is_error);
  return (
    <details className="group mt-1.5 rounded-xl border border-line bg-surface text-sm">
      <summary className="flex cursor-pointer list-none items-center gap-2 rounded-xl px-3 py-2 text-ink-muted hover:text-ink [&::-webkit-details-marker]:hidden">
        <IconChevronRight className="size-4 shrink-0 transition-transform group-open:rotate-90" aria-hidden />
        <span className="font-medium whitespace-nowrap">{tp("conversations.actions", calls.length)}</span>
        <span className="min-w-0 truncate text-xs text-ink-subtle">
          {calls.map((call) => t(TOOL_LABELS[call.tool_name])).join(", ")}
        </span>
        {failed ? (
          <Badge tone="danger" className="ml-auto">
            {t("conversations.toolError")}
          </Badge>
        ) : null}
      </summary>
      <ol className="space-y-3 border-t border-line px-3 py-3">
        {calls.map((call, index) => (
          <li key={index} className="space-y-1.5">
            <p className="flex flex-wrap items-center gap-2 font-medium text-ink">
              {t(TOOL_LABELS[call.tool_name])}
              <code className="text-xs font-normal text-ink-subtle">{call.tool_name}</code>
              {call.is_error ? <Badge tone="danger">{t("conversations.toolError")}</Badge> : null}
            </p>
            <JsonBlock label={t("conversations.toolInput")} json={call.input_json} />
            <JsonBlock label={t("conversations.toolResult")} json={call.result_json} />
          </li>
        ))}
      </ol>
    </details>
  );
}

function JsonBlock({ label, json }: { label: string; json: string }) {
  return (
    <div>
      <p className="text-xs text-ink-subtle">{label}</p>
      <pre
        dir="ltr"
        className="mt-0.5 max-h-60 overflow-auto rounded-lg bg-surface-muted px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap text-ink [overflow-wrap:anywhere]"
      >
        {prettyJson(json)}
      </pre>
    </div>
  );
}

function memberName(
  member: { display_name?: string | null; email?: string | null; phone_number?: string | null } | undefined,
): string | null {
  return member ? (member.display_name ?? member.email ?? member.phone_number ?? null) : null;
}

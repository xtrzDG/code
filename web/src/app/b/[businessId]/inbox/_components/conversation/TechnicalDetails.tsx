"use client";

/**
 * "Technical details": what is behind a message (the model, tokens and AI
 * cost for platform admins; the exact requests the assistant made to the
 * business's data, with their answers, for everyone who opens it) and the
 * conversation's totals. Closed by default for everyone, who read the
 * plain actions above it; a person's own open or close is remembered
 * (_lib/technicalDetails).
 */

import { useEffect, useRef, type ReactNode } from "react";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconChevronRight } from "@/components/icons";
import { TOOL_LABELS } from "@/components/insights/labels";
import { formatMicroUsd } from "@/components/insights/numbers";
import type { MessageView, ToolCallView } from "@/components/insights/types";
import { Badge } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { prettyJson } from "../../_lib/conversationModel";
import { localChoiceStorage, readDetailsChoice, startsOpen, writeDetailsChoice } from "../../_lib/technicalDetails";
import type { UsageTotals } from "../../_lib/conversationUsage";

function Disclosure({ label, children, className }: { label: string; children: ReactNode; className?: string }) {
  const { me } = useBusiness();
  const details = useRef<HTMLDetailsElement>(null);
  const userId = me.user.id;

  useEffect(() => {
    if (details.current) {
      details.current.open = startsOpen(readDetailsChoice(localChoiceStorage(), userId));
    }
  }, [userId]);

  // Only a person's own click is remembered (opening by default is not a choice).
  const remember = () => {
    writeDetailsChoice(localChoiceStorage(), userId, details.current?.open ? "closed" : "open");
  };

  return (
    <details
      ref={details}
      className={cn("group w-fit max-w-full rounded-xl border border-line bg-surface text-start text-sm open:w-full", className)}
    >
      <summary
        onClick={remember}
        className="flex cursor-pointer list-none items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium text-ink-subtle hover:text-ink [&::-webkit-details-marker]:hidden">
        <IconChevronRight className="size-3.5 shrink-0 transition-transform group-open:rotate-90 rtl:-scale-x-100" aria-hidden />
        {label}
      </summary>
      <div className="space-y-3 border-t border-line px-3 py-3">{children}</div>
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

function ToolCallDetails({ call }: { call: ToolCallView }) {
  const { t } = useI18n();
  return (
    <div className="space-y-1.5">
      <p className="flex flex-wrap items-center gap-2 font-medium text-ink">
        {t(TOOL_LABELS[call.tool_name])}
        <code className="text-xs font-normal text-ink-subtle">{call.tool_name}</code>
        {call.is_error ? <Badge tone="danger">{t("conversations.toolError")}</Badge> : null}
      </p>
      <JsonBlock label={t("conversations.toolInput")} json={call.input_json} />
      <JsonBlock label={t("conversations.toolResult")} json={call.result_json} />
    </div>
  );
}

/** Whether a message has anything behind it to show. */
export function hasTechnicalDetails(message: MessageView, isPlatformAdmin: boolean): boolean {
  return (message.tool_calls?.length ?? 0) > 0 || (isPlatformAdmin && Boolean(message.model_id || message.input_tokens));
}

/** The technical details of one message. */
export function MessageTechnicalDetails({ message, className }: { message: MessageView; className?: string }) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const { isPlatformAdmin } = useBusiness();
  const tokens = message.input_tokens + message.output_tokens;
  return (
    <Disclosure label={t("inboxCard.technical.message")} className={className}>
      {isPlatformAdmin && (message.model_id || tokens > 0) ? (
        <p className="text-xs text-ink-muted">
          {[
            message.model_id,
            t("conversations.messageTokens", { count: format.number(tokens) }),
            formatMicroUsd(message.cost_micro_usd, locale),
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
      ) : null}
      {(message.tool_calls ?? []).map((call, index) => (
        <ToolCallDetails key={index} call={call} />
      ))}
    </Disclosure>
  );
}

/** The conversation's totals (platform admins: tokens and AI cost; everyone: the update that answered). */
export function ConversationTechnicalDetails({
  totals,
  versionId,
}: {
  totals: UsageTotals;
  versionId: string;
}) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const { isPlatformAdmin } = useBusiness();
  return (
    <Disclosure label={t("inboxCard.technical.title")}>
      <p className="text-xs text-ink-muted">{t("inboxCard.technical.hint")}</p>
      <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1.5 text-xs">
        <dt className="text-ink-subtle">{t("inboxCard.technical.version")}</dt>
        <dd className="font-mono break-all text-ink">{versionId}</dd>
        {isPlatformAdmin ? (
          <>
            <dt className="text-ink-subtle">{t("inboxCard.technical.tokens")}</dt>
            <dd className="text-ink tabular-nums">
              {t("conversations.usage.tokensValue", {
                input: format.number(totals.inputTokens),
                output: format.number(totals.outputTokens),
              })}
            </dd>
            <dt className="text-ink-subtle">{t("inboxCard.technical.cost")}</dt>
            <dd className="text-ink tabular-nums">{formatMicroUsd(totals.costMicroUsd, locale)}</dd>
          </>
        ) : null}
      </dl>
    </Disclosure>
  );
}

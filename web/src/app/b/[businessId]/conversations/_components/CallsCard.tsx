"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconChevronRight } from "@/components/icons";
import type { CallView } from "@/components/insights/types";
import { Badge, Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { CALL_OUTCOMES, formatCallDuration } from "./conversationModel";

/**
 * The phone calls of the conversation: when, how long, what came out of
 * them, the call transcript and where the recording is kept (the voice
 * platform's reference; recordings are deleted after the retention period).
 */
export function CallsCard({ calls }: { calls: readonly CallView[] }) {
  const { t, tp } = useI18n();
  return (
    <Card title={tp("conversations.calls.title", calls.length)}>
      <ol className="space-y-4">
        {calls.map((call) => (
          <CallItem key={call.id} call={call} />
        ))}
      </ol>
      <p className="mt-4 text-xs text-ink-subtle">{t("conversations.calls.auditNote")}</p>
    </Card>
  );
}

function CallItem({ call }: { call: CallView }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  return (
    <li className="rounded-xl border border-line p-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
        <span className="font-medium text-ink">{format.dateTime(call.started_at)}</span>
        <span className="text-ink-muted tabular-nums" dir="ltr">
          {formatCallDuration(call.duration_seconds)}
        </span>
        {call.outcome ? <Badge tone="neutral">{t(CALL_OUTCOMES[call.outcome])}</Badge> : null}
        {call.from_phone_number ? (
          <span className="text-ink-muted">
            {t("conversations.calls.from")}{" "}
            <span dir="ltr" className="tabular-nums">
              {call.from_phone_number}
            </span>
          </span>
        ) : null}
      </div>
      <dl className="mt-3 space-y-2 text-sm">
        <div>
          <dt className="text-ink-muted">{t("conversations.calls.recording")}</dt>
          <dd className="text-ink">
            {call.recording_path ? (
              <code dir="ltr" className="text-xs break-all text-ink-muted">
                {call.recording_path}
              </code>
            ) : (
              t("conversations.calls.noRecording")
            )}
          </dd>
        </div>
      </dl>
      {call.transcript ? (
        <details className="group mt-3 rounded-xl border border-line bg-surface text-sm">
          <summary className="flex cursor-pointer list-none items-center gap-2 rounded-xl px-3 py-2 text-ink-muted hover:text-ink [&::-webkit-details-marker]:hidden">
            <IconChevronRight className="size-4 shrink-0 transition-transform group-open:rotate-90" aria-hidden />
            <span className="font-medium">{t("conversations.calls.transcript")}</span>
          </summary>
          <pre
            dir="auto"
            className="max-h-80 overflow-auto border-t border-line px-3 py-3 font-sans text-sm leading-relaxed whitespace-pre-wrap text-ink [overflow-wrap:anywhere]"
          >
            {call.transcript}
          </pre>
        </details>
      ) : (
        <p className="mt-3 text-sm text-ink-muted">{t("conversations.calls.noTranscript")}</p>
      )}
    </li>
  );
}

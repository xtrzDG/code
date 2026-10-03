"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconChevronRight } from "@/components/icons";
import type { CallView } from "@/components/insights/types";
import { Alert, Badge, Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { formatPhone } from "@/lib/phone";

import { CallRecordingPlayer } from "./CallRecordingPlayer";
import { callGuardBadge, callGuardFindings } from "../../_lib/callGuard";
import { pickCallSummary } from "../../_lib/callSummary";
import { CALL_OUTCOMES, formatCallDuration } from "../../_lib/conversationModel";

/**
 * The phone calls of the conversation: when, how long, what came out of
 * them, the summary written after the call (in the reader's language when
 * there is one), what the after-call check of the assistant's spoken
 * values found, the call transcript and a player for the recording (kept
 * by the voice platform, loaded only on play; recordings are deleted
 * after the retention period).
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
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const guardBadge = callGuardBadge(call);
  const summary = pickCallSummary(call, locale);
  return (
    <li className="rounded-xl border border-line p-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
        <span className="font-medium text-ink">{format.dateTime(call.started_at)}</span>
        <span className="text-ink-muted tabular-nums" dir="ltr">
          {formatCallDuration(call.duration_seconds)}
        </span>
        {call.outcome ? <Badge tone="neutral">{t(CALL_OUTCOMES[call.outcome])}</Badge> : null}
        {guardBadge ? <Badge tone={guardBadge.tone}>{t(guardBadge.label)}</Badge> : null}
        {call.from_phone_number ? (
          <span className="text-ink-muted">
            {t("conversations.calls.from")}{" "}
            <span dir="ltr" className="whitespace-nowrap tabular-nums">
              {formatPhone(call.from_phone_number)}
            </span>
          </span>
        ) : null}
      </div>
      {summary ? (
        <div className="mt-3 text-sm">
          <p className="text-ink-muted">{t("conversations.calls.summary")}</p>
          <p lang={summary.language} dir="auto" className="mt-1 text-ink">
            {summary.text}
          </p>
        </div>
      ) : null}
      <CallGuardFindingsNotice call={call} />
      <dl className="mt-3 space-y-2 text-sm">
        <div>
          <dt className="text-ink-muted">{t("conversations.calls.recording")}</dt>
          <dd className="mt-1 text-ink">
            {call.recording_path ? (
              <CallRecordingPlayer
                callId={call.id}
                label={t("conversations.calls.playerLabel", { date: format.dateTime(call.started_at) })}
                playLabel={t("conversations.calls.playLabel", { date: format.dateTime(call.started_at) })}
              />
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

/** The values the assistant said that the business data does not back. */
function CallGuardFindingsNotice({ call }: { call: CallView }) {
  const { t } = useI18n();
  const findings = callGuardFindings(call);
  if (findings === null) {
    return null;
  }
  return (
    <Alert tone="warning" title={t(findings.title)} className="mt-3">
      <p>{t("conversations.calls.guard.valuesLabel")}</p>
      <ul className="mt-1.5 flex flex-wrap gap-1.5" aria-label={t("conversations.calls.guard.valuesLabel")}>
        {findings.values.map((value) => (
          <li
            key={value}
            dir="auto"
            className="rounded-lg border border-warning/30 bg-surface px-2 py-0.5 font-medium text-ink tabular-nums"
          >
            {value}
          </li>
        ))}
      </ul>
      <p className="mt-2">{t("conversations.calls.guard.hint")}</p>
    </Alert>
  );
}

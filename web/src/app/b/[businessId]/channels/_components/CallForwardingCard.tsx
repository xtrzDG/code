"use client";

import { api } from "@/api/client";
import { useApiQuery } from "@/api/hooks";
import type { Schema } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconChevronDown, IconInfo } from "@/components/icons";
import { Card, ErrorState, LoadingBlock } from "@/components/ui";
import { CopyButton } from "@/components/workspace/CopyButton";
import { IconPhone } from "@/components/workspace/icons";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import { dialHref, sortForwardingCodes, type CallForwardingCondition } from "../_lib/channels";

const CONDITION_LABELS: Record<CallForwardingCondition, MessageKey> = {
  no_answer: "channels.forwarding.condition.no_answer",
  busy: "channels.forwarding.condition.busy",
  unreachable: "channels.forwarding.condition.unreachable",
  cancel_all: "channels.forwarding.condition.cancel_all",
};

/**
 * Forwarding of missed, busy and unreachable calls to the assistant's number:
 * steps and GSM codes (per operator where known) in the interface language.
 */
export function CallForwardingCard() {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const instructions = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/call-forwarding-instructions", {
        params: { path: { business_id: business.id }, query: { language: locale } },
      }),
    [business.id, locale],
  );
  const data = instructions.data;

  return (
    <Card title={t("channels.forwarding.title")} description={t("channels.forwarding.description")}>
      {instructions.error && !data ? (
        <ErrorState error={instructions.error} onRetry={instructions.reload} className="py-6" />
      ) : !data ? (
        <LoadingBlock label={t("common.loading")} className="min-h-24" />
      ) : (
        <div className="space-y-6" lang={data.display_language}>
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-surface-muted/60 px-4 py-3">
            <div className="flex items-center gap-3">
              <span className="flex size-9 items-center justify-center rounded-full bg-accent-soft text-accent" aria-hidden>
                <IconPhone className="size-5" />
              </span>
              <div>
                <p className="text-xs text-ink-subtle">{t("channels.forwarding.assistantNumber")}</p>
                <p className="text-lg font-semibold tracking-wide text-ink" dir="ltr">
                  {data.assistant_phone_number_display}
                </p>
              </div>
            </div>
            <CopyButton value={data.assistant_phone_number} />
          </div>

          <section aria-labelledby="forwarding-steps" className="space-y-2">
            <h3 id="forwarding-steps" className="text-sm font-semibold text-ink">
              {t("channels.forwarding.stepsTitle")}
            </h3>
            <ol className="list-decimal space-y-1.5 pl-5 text-sm text-ink-muted marker:font-medium marker:text-ink-subtle">
              {data.steps.map((step, index) => (
                <li key={index}>{step}</li>
              ))}
            </ol>
          </section>

          <section aria-labelledby="forwarding-codes" className="space-y-2">
            <h3 id="forwarding-codes" className="text-sm font-semibold text-ink">
              {t("channels.forwarding.codesTitle")}
            </h3>
            <ForwardingCodes codes={data.codes} />
          </section>

          {data.carriers && data.carriers.length > 0 ? (
            <section aria-labelledby="forwarding-carriers" className="space-y-2">
              <h3 id="forwarding-carriers" className="text-sm font-semibold text-ink">
                {t("channels.forwarding.carriersTitle")}
              </h3>
              <div className="divide-y divide-line rounded-xl border border-line">
                {data.carriers.map((carrier) => (
                  <details key={carrier.carrier_name} className="group">
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-medium text-ink hover:bg-surface-muted/60 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus [&::-webkit-details-marker]:hidden">
                      {carrier.carrier_name}
                      <IconChevronDown className="size-4 text-ink-subtle transition-transform group-open:rotate-180" aria-hidden />
                    </summary>
                    <div className="space-y-3 px-4 pb-4">
                      {carrier.note ? <p className="text-sm text-ink-muted">{carrier.note}</p> : null}
                      <ForwardingCodes codes={carrier.codes} />
                    </div>
                  </details>
                ))}
              </div>
            </section>
          ) : null}

          {data.notes && data.notes.length > 0 ? (
            <section aria-labelledby="forwarding-notes" className="rounded-xl bg-info-soft/70 p-4">
              <h3 id="forwarding-notes" className="flex items-center gap-2 text-sm font-semibold text-info">
                <IconInfo className="size-4" aria-hidden />
                {t("channels.forwarding.notesTitle")}
              </h3>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink-muted">
                {data.notes.map((note, index) => (
                  <li key={index}>{note}</li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      )}
    </Card>
  );
}

function ForwardingCodes({ codes }: { codes: readonly Schema<"CallForwardingCode">[] }) {
  const { t } = useI18n();
  return (
    <ul className="divide-y divide-line rounded-xl border border-line">
      {sortForwardingCodes(codes).map((code) => (
        <li key={code.condition} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
          <div className="min-w-0 flex-1 basis-48">
            <p className="text-sm font-medium text-ink">{t(CONDITION_LABELS[code.condition])}</p>
            <p className="text-xs text-ink-muted">{code.description}</p>
          </div>
          <div className="flex items-center gap-1">
            <code dir="ltr" className="rounded-md bg-surface-muted px-2 py-1 font-mono text-sm text-ink">
              {code.dial_code}
            </code>
            <CopyButton value={code.dial_code} iconOnly label={`${t("workspace.copy")} ${code.dial_code}`} />
            <a
              href={dialHref(code.dial_code)}
              className="rounded-lg px-2 py-1 text-sm font-medium text-accent hover:bg-accent-soft focus-visible:outline-2 focus-visible:outline-focus sm:hidden"
              aria-label={t("channels.forwarding.dialLabel", { code: code.dial_code })}
            >
              {t("channels.forwarding.dial")}
            </a>
          </div>
        </li>
      ))}
    </ul>
  );
}

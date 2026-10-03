"use client";

/**
 * Pieces of the launch screen: what is ready (each step with a way back
 * to fix it), the agreement to accept, and what stopped a launch with
 * where to fix each reason.
 */

import Link from "next/link";
import { useState } from "react";

import type { Schema } from "@/api/types";
import { DpaReader } from "@/app/b/[businessId]/settings/_components/privacy/DpaReader";
import { IconAlert, IconCheck, IconFile } from "@/components/icons";
import { Badge, Button, Checkbox, buttonClasses } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";
import { fixPlace, stepStates, TUNNEL_STEPS, type RailState, type TunnelStep } from "@/lib/tunnel/steps";

const STATE_TONES = { done: "success", skipped: "neutral", todo: "warning" } as const;

export function LaunchChecklist({ setup, onFix }: { setup: Schema<"SetupView">; onFix: (step: TunnelStep) => void }) {
  const { t } = useI18n();
  const states = stepStates(setup);
  const steps = TUNNEL_STEPS.filter((step) => step !== "launch");
  return (
    <section aria-labelledby="tunnel-checklist" className="space-y-3">
      <h2 id="tunnel-checklist" className="text-lg font-semibold text-ink">
        {t("tunnelLaunch.launch.checklist")}
      </h2>
      <ul className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface/85 backdrop-blur-sm">
        {steps.map((step) => {
          const state: RailState = states[step];
          return (
            <li key={step} className="flex min-h-12 items-center gap-3 px-4 py-2">
              <span className="min-w-0 flex-1 text-sm font-medium text-ink">{t(`tunnel.steps.${step}`)}</span>
              <Badge tone={STATE_TONES[state]}>{t(`tunnelLaunch.launch.state.${state}`)}</Badge>
              {state === "done" ? (
                <IconCheck className="size-4 text-success" aria-hidden />
              ) : (
                <Button variant="ghost" size="sm" onClick={() => onFix(step)}>
                  {t("tunnelLaunch.launch.fix")}
                </Button>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export function AgreementField({
  version,
  hasText,
  isAgreed,
  onAgree,
  showError,
}: {
  version: string;
  hasText: boolean;
  isAgreed: boolean;
  onAgree: (agreed: boolean) => void;
  showError: boolean;
}) {
  const { t } = useI18n();
  const [isReading, setReading] = useState(false);
  return (
    <div className="space-y-2 rounded-2xl border border-line bg-surface/85 p-4 backdrop-blur-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <Checkbox
          id="tunnel-dpa"
          checked={isAgreed}
          onChange={(event) => onAgree(event.target.checked)}
          label={t("tunnelLaunch.launch.agreement")}
          description={t("tunnelLaunch.launch.agreementHint")}
          aria-invalid={showError || undefined}
        />
        {hasText ? (
          <Button variant="ghost" size="sm" leadingIcon={<IconFile className="size-4" aria-hidden />} onClick={() => setReading(true)}>
            {t("tunnelLaunch.launch.readAgreement")}
          </Button>
        ) : null}
      </div>
      {showError ? (
        <p className="text-sm text-danger" role="alert">
          {t("tunnelLaunch.launch.agreementRequired")}
        </p>
      ) : null}
      <DpaReader
        open={isReading}
        version={version}
        canConfirm
        onClose={() => setReading(false)}
        onConfirm={() => {
          onAgree(true);
          setReading(false);
        }}
      />
    </div>
  );
}

export function LaunchAttention({
  businessId,
  view,
  onFix,
}: {
  businessId: string;
  view: Schema<"ApplyChangesView">;
  onFix: (step: TunnelStep) => void;
}) {
  const { t } = useI18n();
  const reasons = view.attention ?? [];
  const versionLink = view.assistant_version_id
    ? `${businessPath(businessId, "assistant/versions")}/${view.assistant_version_id}`
    : businessPath(businessId, "assistant/versions");

  return (
    <section aria-labelledby="tunnel-attention" className="space-y-3 rounded-2xl border border-warning/40 bg-warning-soft/40 p-4 backdrop-blur-sm sm:p-5">
      <h2 id="tunnel-attention" className="flex items-center gap-2 text-lg font-semibold text-ink">
        <IconAlert className="size-5 text-warning" aria-hidden />
        {t("tunnelLaunch.launch.attentionTitle")}
      </h2>
      <p className="text-sm text-ink-muted">{t("tunnelLaunch.launch.attentionText")}</p>
      <ul className="space-y-2">
        {reasons.map((reason) => {
          const place = fixPlace(reason.action);
          return (
            <li key={reason.code} className="flex flex-col gap-2 rounded-xl bg-surface/90 p-3 sm:flex-row sm:items-center">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-ink">{reason.message}</p>
                {reason.details?.length ? (
                  <ul className="mt-1 list-disc ps-5 text-xs text-ink-muted">
                    {reason.details.map((detail) => (
                      <li key={detail}>{detail}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
              {place.kind === "step" && place.step !== "launch" ? (
                <Button variant="secondary" size="sm" onClick={() => onFix(place.step)}>
                  {reason.action.label}
                </Button>
              ) : place.kind === "billing" ? (
                <Link href={businessPath(businessId, "settings/billing")} className={buttonClasses({ variant: "secondary", size: "sm" })}>
                  {reason.action.label}
                </Link>
              ) : place.kind === "checks" ? (
                <Link href={versionLink} className={buttonClasses({ variant: "secondary", size: "sm" })}>
                  {t("tunnelLaunch.launch.seeChecks")}
                </Link>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

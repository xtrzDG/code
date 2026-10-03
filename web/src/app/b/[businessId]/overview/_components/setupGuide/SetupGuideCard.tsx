"use client";

/**
 * The Overview's setup guide (GET …/setup → `guide`). Before the launch:
 * the setup's steps, each opening the tunnel at its screen, and "Continue
 * setup". After it: the way to the first customers (a message from the
 * owner's phone, a second channel, the link and QR card where customers
 * see them), the first wins, and once everything is done or skipped a
 * short "all set" the owner puts away.
 */

import { useState } from "react";

import type { Schema } from "@/api/types";
import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconArrowRight, IconCheckCircle } from "@/components/icons";
import { FadeIn } from "@/components/motion";
import { ProgressRing } from "@/components/setupGuide/ProgressRing";
import { Button, ButtonLink } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { setupPath } from "@/lib/navigation";
import { guideRows, reachedWins } from "@/lib/setupGuide/guide";

import { PhoneTestPanel } from "./PhoneTestPanel";
import { SetupGuideRow } from "./SetupGuideRow";
import { useSetupGuideActions } from "./useSetupGuideActions";
import { GuideWins } from "./GuideWins";

type SetupView = Schema<"SetupView">;

export function SetupGuideCard({ setup, isFinished }: { setup: SetupView; isFinished: boolean }) {
  const { t, tp } = useI18n();
  const format = useBusinessFormat();
  const businessId = setup.business_id;
  const actions = useSetupGuideActions(businessId);
  const [isPhoneOpen, setPhoneOpen] = useState(false);
  const guide = setup.guide;
  const wins = reachedWins(setup);

  if (isFinished) {
    return (
      <FadeIn as="section" tone="cabinet" aria-labelledby="setup-guide-title" id="setup-guide" className="rounded-2xl border border-line bg-surface p-4 sm:p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <IconCheckCircle className="size-8 shrink-0 text-success" aria-hidden />
          <div className="min-w-0 flex-1 space-y-1">
            <h2 id="setup-guide-title" className="text-base font-semibold text-ink">
              {t("setupGuide.finished.title")}
            </h2>
            <p className="text-sm text-ink-muted">{t("setupGuide.finished.description")}</p>
          </div>
          <Button variant="secondary" size="sm" onClick={() => void actions.dismiss.run()} isLoading={actions.dismiss.isPending}>
            {t("setupGuide.finished.dismiss")}
          </Button>
        </div>
        {wins.length > 0 ? <GuideWins wins={wins} /> : null}
      </FadeIn>
    );
  }

  const rows = guideRows(setup, businessId);
  const percentLabel = t("setupGuide.ring.label", { percent: guide.percent });
  return (
    <FadeIn as="section" tone="cabinet" aria-labelledby="setup-guide-title" id="setup-guide" className="rounded-2xl border border-line bg-surface p-4 sm:p-5">
      <div className="flex flex-wrap items-start gap-4">
        <ProgressRing percent={guide.percent} size={48} label={percentLabel} />
        <div className="min-w-0 flex-1 space-y-1">
          <h2 id="setup-guide-title" className="text-base font-semibold text-ink">
            {t(setup.is_live ? "setupGuide.titleLive" : "setupGuide.titleSetup")}
          </h2>
          <p className="text-sm text-ink-muted">
            {setup.is_live && setup.went_live_at
              ? t("setupGuide.liveSince", { date: format.date(setup.went_live_at) })
              : t("setupGuide.descriptionSetup")}
            {guide.minutes_left > 0 ? ` · ${tp("setupGuide.minutesLeft", guide.minutes_left)}` : ""}
          </p>
        </div>
        {setup.is_live ? null : (
          <ButtonLink href={setupPath(businessId)} trailingIcon={<IconArrowRight className="size-4" aria-hidden />} className="w-full sm:w-auto">
            {t("setupGuide.continueSetup")}
          </ButtonLink>
        )}
      </div>
      <ol className="mt-4 divide-y divide-line border-t border-line pt-4">
        {rows.map((row) => (
          <SetupGuideRow
            key={row.step.code}
            row={row}
            isOpen={row.kind === "phone" && isPhoneOpen}
            onToggle={() => setPhoneOpen((open) => !open)}
            onSkip={(isSkipped) => void actions.skip.run(row.step.code, isSkipped)}
            isBusy={actions.skip.isPending}
          >
            {row.kind === "phone" ? (
              <PhoneTestPanel setup={setup} businessId={businessId} onStart={() => void actions.startPhoneCheck.run()} />
            ) : null}
          </SetupGuideRow>
        ))}
      </ol>
      {setup.is_live ? null : <p className="mt-3 text-xs text-ink-subtle">{t("setupGuide.afterLaunchHint")}</p>}
      {wins.length > 0 ? <GuideWins wins={wins} /> : null}
    </FadeIn>
  );
}

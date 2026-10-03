"use client";

/**
 * Step 8, "Ready to go live?": what is ready (with a way back to each
 * step), the data processing agreement, the free trial, and "Launch my
 * assistant". The launch then plays out on screen: getting everything
 * ready, trying test conversations, switching it on; anything that stops
 * it is listed with where to fix it, and "Try again".
 */

import Link from "next/link";

import { Alert } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import { StepScreen } from "../StepScreen";
import type { StepContext } from "../flow/stepContext";
import { AgreementField, LaunchAttention, LaunchChecklist } from "./LaunchParts";
import { LaunchProgress } from "./LaunchProgress";
import { useLaunch } from "./useLaunch";

function TrialNote({ businessId, trial }: { businessId: string; trial: ReturnType<typeof useLaunch>["trial"] }) {
  const { t, tp } = useI18n();
  if (trial.isAvailable === null || trial.hasPlan) {
    return null;
  }
  if (!trial.isAvailable) {
    return (
      <Alert
        tone="warning"
        action={
          <Link href={businessPath(businessId, "settings/billing")} className="font-medium underline">
            {t("tunnelLaunch.launch.plans")}
          </Link>
        }
      >
        {t("tunnelLaunch.launch.planNeeded")}
      </Alert>
    );
  }
  return <p className="text-sm text-ink-muted">{trial.days ? tp("tunnelLaunch.launch.trial", trial.days) : t("tunnelLaunch.launch.trialPlain")}</p>;
}

export function LaunchScreen({ ctx }: { ctx: StepContext }) {
  const { t } = useI18n();
  const launch = useLaunch(ctx);
  const { phase, agreement } = launch;
  const isRunning = phase === "running" || phase === "live";

  return (
    <StepScreen
      step="launch"
      title={t("tunnelLaunch.launch.title")}
      text={isRunning ? t("tunnelLaunch.launch.running") : t("tunnelLaunch.launch.text")}
      actions={{
        onBack: isRunning ? undefined : ctx.back,
        onContinue: isRunning ? undefined : () => void launch.launch(),
        continueLabel: phase === "attention" ? t("tunnelLaunch.launch.tryAgain") : t("tunnelLaunch.launch.start"),
        busyLabel: t("tunnelLaunch.launch.starting"),
        isBusy: launch.isStarting,
        canContinue: !agreement.isLoading,
      }}
    >
      <div className="space-y-6">
        {phase === "running" || phase === "live" || phase === "attention" ? <LaunchProgress view={launch.view} /> : null}
        {phase === "attention" ? <LaunchAttention businessId={ctx.businessId} view={launch.view} onFix={ctx.goTo} /> : null}
        {phase === "idle" ? <LaunchChecklist setup={ctx.setup} onFix={ctx.goTo} /> : null}
        {!isRunning && !agreement.isLoading ? (
          agreement.isAccepted ? (
            <p className="text-sm text-ink-muted">{t("tunnelLaunch.launch.agreementAccepted")}</p>
          ) : (
            <AgreementField
              version={agreement.version}
              hasText={agreement.hasText}
              isAgreed={agreement.isAgreed}
              onAgree={agreement.setAgreed}
              showError={agreement.showError}
            />
          )
        ) : null}
        {!isRunning ? <TrialNote businessId={ctx.businessId} trial={launch.trial} /> : null}
      </div>
    </StepScreen>
  );
}

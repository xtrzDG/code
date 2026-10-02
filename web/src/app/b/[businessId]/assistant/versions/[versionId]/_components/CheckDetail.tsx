"use client";

import { useI18n } from "@/i18n/client";
import type { GoLiveCheck, GoLiveReadiness } from "@/lib/assistant/goLive";

import { GapList } from "./goLiveFixes";

/** What one check says, in the UI language, from its code and details. */
export function CheckDetail({ check, readiness }: { check: GoLiveCheck; readiness: GoLiveReadiness }) {
  const { t } = useI18n();
  const details = check.details ?? [];
  switch (check.code) {
    case "subscription_or_trial":
      if (check.is_ok) {
        return <>{readiness.subscription_status === "trialing" ? t("assistant.checklist.billingTrial") : t("assistant.checklist.billingActive")}</>;
      }
      return <>{details[0] === "none" ? t("assistant.checklist.billingStartTrial") : t("assistant.checklist.billingMissing")}</>;
    case "dpa":
      return (
        <>{check.is_ok ? t("assistant.checklist.dpaOk") : t("assistant.checklist.dpaMissing", { version: readiness.dpa_document_version })}</>
      );
    case "profile_gaps":
      return check.is_ok ? (
        <>{t("assistant.checklist.profileOk")}</>
      ) : (
        <>
          {t("assistant.checklist.profileMissing")}
          <GapList kinds={details} />
        </>
      );
    case "staff_contact":
      return <>{check.is_ok ? t("assistant.checklist.staffContactOk") : t("assistant.checklist.staffContactMissing")}</>;
    case "autotests":
      return <AutotestsDetail check={check} readiness={readiness} />;
    case "voice_configuration":
      return (
        <>
          {check.is_ok
            ? t("assistant.checklist.voiceOk")
            : check.is_blocking
              ? t("assistant.checklist.voiceMissing")
              : t("assistant.checklist.voiceWarning")}
        </>
      );
  }
}

function AutotestsDetail({ check, readiness }: { check: GoLiveCheck; readiness: GoLiveReadiness }) {
  const { t } = useI18n();
  const details = check.details ?? [];
  const run = readiness.autotest_run;
  if (check.is_ok) {
    return <>{t("assistant.checklist.autotestsOk")}</>;
  }
  if (details[0] === "testing") {
    return (
      <>
        {run && run.status === "running" && run.scenario_count > 0
          ? t("assistant.checklist.autotestsProgress", { done: run.completed_count, total: run.scenario_count })
          : t("assistant.checklist.autotestsRunning")}
      </>
    );
  }
  if (!run) {
    return <>{t("assistant.checklist.autotestsMissing")}</>;
  }
  if (run.status === "errored") {
    return <>{t("assistant.checklist.autotestsErrored")}</>;
  }
  if (run.is_passed && !run.is_full_coverage) {
    return <>{t("assistant.checklist.autotestsPartial")}</>;
  }
  return <>{t("assistant.checklist.autotestsFailed")}</>;
}

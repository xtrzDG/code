"use client";

import Link from "next/link";
import { useEffect, useRef, type ReactNode } from "react";

import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { useApiQuery } from "@/api/hooks";
import type { Schema } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconCheckCircle, IconXCircle } from "@/components/content/icons";
import { IconAlert, IconClock } from "@/components/icons";
import { Card, ErrorState, LoadingBlock } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import {
  blockingChecks,
  checkState,
  isTestingRefusal,
  type CheckState,
  type GoLiveCheck,
  type GoLiveCheckCode,
  type GoLiveReadiness,
  type Refusal,
  type RefusalCode,
} from "@/lib/assistant";
import { businessPath } from "@/lib/navigation";

type ProfileGapKind = Schema<"ProfileGapKind">;

export const GAP_KIND_LABELS: Record<ProfileGapKind, MessageKey> = {
  missing_required_answer: "assistant.gapKinds.missing_required_answer",
  no_opening_hours: "assistant.gapKinds.no_opening_hours",
  no_address: "assistant.gapKinds.no_address",
  no_handoff_contact: "assistant.gapKinds.no_handoff_contact",
  no_booking_rules: "assistant.gapKinds.no_booking_rules",
  no_resources: "assistant.gapKinds.no_resources",
  no_priced_items: "assistant.gapKinds.no_priced_items",
  no_faq: "assistant.gapKinds.no_faq",
  unanswered_question: "assistant.gapKinds.unanswered_question",
};

function isGapKind(value: string): value is ProfileGapKind {
  return value in GAP_KIND_LABELS;
}

const CHECK_TITLES: Record<GoLiveCheckCode, MessageKey> = {
  subscription_or_trial: "assistant.checklist.billing",
  dpa: "assistant.checklist.dpa",
  profile_gaps: "assistant.checklist.profile",
  staff_contact: "assistant.checklist.staffContact",
  autotests: "assistant.checklist.autotests",
  voice_configuration: "assistant.checklist.voice",
};

const STATE_LABELS: Record<CheckState, MessageKey> = {
  ok: "assistant.checklist.state.ok",
  missing: "assistant.checklist.state.missing",
  pending: "assistant.checklist.state.pending",
  warning: "assistant.checklist.state.warning",
};

/** Where an owner fixes each launch condition. */
function useFixLinks(): Partial<Record<GoLiveCheckCode, { href: string; label: MessageKey }>> {
  const { business } = useBusiness();
  return {
    subscription_or_trial: { href: businessPath(business.id, "billing"), label: "assistant.checklist.fixBilling" },
    dpa: { href: `${businessPath(business.id, "settings")}#privacy`, label: "assistant.checklist.fixDpa" },
    profile_gaps: { href: businessPath(business.id, "onboarding"), label: "assistant.checklist.fixProfile" },
    staff_contact: { href: `${businessPath(business.id, "settings")}#notifications`, label: "assistant.checklist.fixStaffContact" },
  };
}

function StateIcon({ state }: { state: CheckState }) {
  if (state === "ok") {
    return <IconCheckCircle className="size-5 text-success" aria-hidden />;
  }
  if (state === "pending") {
    return <IconClock className="size-5 text-info" aria-hidden />;
  }
  if (state === "warning") {
    return <IconAlert className="size-5 text-warning" aria-hidden />;
  }
  return <IconXCircle className="size-5 text-danger" aria-hidden />;
}

function CheckRow({ state, title, detail, action }: { state: CheckState; title: string; detail?: ReactNode; action?: ReactNode }) {
  const { t } = useI18n();
  return (
    <li className="flex items-start gap-3 py-3">
      <span className="mt-0.5 shrink-0">
        <StateIcon state={state} />
      </span>
      <div className="min-w-0 flex-1 sm:flex sm:items-center sm:justify-between sm:gap-4">
        <div className="min-w-0">
          <p className="text-sm font-medium text-ink">
            {title}
            <span className="sr-only">: {t(STATE_LABELS[state])}</span>
          </p>
          {detail ? <div className="mt-0.5 text-sm text-ink-muted">{detail}</div> : null}
        </div>
        {action ? <div className="mt-1.5 sm:mt-0 sm:shrink-0">{action}</div> : null}
      </div>
    </li>
  );
}

function FixLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="text-sm font-medium whitespace-nowrap text-accent hover:underline">
      {children}
    </Link>
  );
}

function ActionButton({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" onClick={onClick} className="text-sm font-medium whitespace-nowrap text-accent hover:underline">
      {children}
    </button>
  );
}

function GapList({ kinds }: { kinds: readonly string[] }) {
  const { t } = useI18n();
  return (
    <ul className="mt-1 list-disc pl-5">
      {kinds.map((kind) => (
        <li key={kind}>{isGapKind(kind) ? t(GAP_KIND_LABELS[kind]) : kind}</li>
      ))}
    </ul>
  );
}

/** What one check says, in the UI language, from its code and details. */
function CheckDetail({ check, readiness }: { check: GoLiveCheck; readiness: GoLiveReadiness }) {
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

/**
 * What must be true before customers get this version, as the API checks
 * it before publishing (GET …/go-live-readiness): the trial or a paid plan,
 * the data processing agreement, a complete profile, a staff contact,
 * passed autotests and, for phone versions, the voice setup. Each missing
 * item links to where the owner fixes it.
 */
export function GoLiveChecklist({
  versionId,
  refreshKey,
  onRunAutotests,
  canRunAutotests,
}: {
  versionId: string;
  /** Changes when the page knows the answer may be out of date (a new status, a poll, a refusal). */
  refreshKey: string;
  onRunAutotests: () => void;
  canRunAutotests: boolean;
}) {
  const { t, tp } = useI18n();
  const { business } = useBusiness();
  const fixLinks = useFixLinks();

  const readiness = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/assistant-versions/{version_id}/go-live-readiness", {
        params: { path: { business_id: business.id, version_id: versionId } },
      }),
    [business.id, versionId],
  );
  const data = readiness.data;
  const { reload } = readiness;
  const shownKey = useRef(refreshKey);
  useEffect(() => {
    if (shownKey.current !== refreshKey) {
      shownKey.current = refreshKey;
      reload();
    }
  }, [refreshKey, reload]);

  let body: ReactNode;
  if (!data && readiness.isLoading) {
    body = <LoadingBlock label={t("common.loading")} />;
  } else if (!data) {
    body = <ErrorState error={readiness.error} onRetry={readiness.reload} />;
  } else {
    const remaining = blockingChecks(data.checks).length;
    body = (
      <>
        <p className="mb-2 text-sm font-medium text-ink" role="status">
          {remaining === 0 ? t("assistant.checklist.ready") : tp("assistant.checklist.remaining", remaining)}
        </p>
        <ul className="-mb-3 divide-y divide-line">
          {data.checks.map((check) => {
            const state = checkState(check);
            const fix = fixLinks[check.code];
            const action =
              state === "ok" || state === "pending" ? undefined : check.code === "autotests" ? (
                canRunAutotests ? (
                  <ActionButton onClick={onRunAutotests}>{t("assistant.autotests.run")}</ActionButton>
                ) : undefined
              ) : fix ? (
                <FixLink href={fix.href}>{t(fix.label)}</FixLink>
              ) : undefined;
            return (
              <CheckRow
                key={check.code}
                state={state}
                title={t(CHECK_TITLES[check.code])}
                detail={<CheckDetail check={check} readiness={data} />}
                action={action}
              />
            );
          })}
        </ul>
      </>
    );
  }

  return (
    <Card title={t("assistant.checklist.title")} description={t("assistant.checklist.description")}>
      {body}
    </Card>
  );
}

const REFUSAL_TEXTS: Record<RefusalCode, MessageKey> = {
  subscription_or_trial: "assistant.refusal.subscription_or_trial",
  dpa: "assistant.refusal.dpa",
  profile_gaps: "assistant.refusal.profile_gaps",
  staff_contact: "assistant.refusal.staff_contact",
  autotests: "assistant.refusal.autotests",
  voice_configuration: "assistant.refusal.voice_configuration",
  version_already_live: "assistant.refusal.version_already_live",
  version_archived: "assistant.refusal.version_archived",
  version_not_archived: "assistant.refusal.version_not_archived",
  force_publish_admin_only: "assistant.refusal.force_publish_admin_only",
};

/** Why publishing (or rolling back) was refused, from the API's reason codes, with links to fix each. */
export function RefusalReasons({
  reasons,
  error,
  onRunAutotests,
}: {
  reasons: readonly Refusal[];
  /** The refused request: its message is shown when the API named no reason. */
  error: ApiError | null;
  onRunAutotests?: () => void;
}) {
  const { t } = useI18n();
  const fixLinks = useFixLinks();

  if (reasons.length === 0) {
    return <p className="text-sm text-ink-muted">{error?.detail ?? t("errors.codes.conflict")}</p>;
  }

  return (
    <ul className="space-y-3">
      {reasons.map((reason, index) => {
        const text =
          reason.code === null
            ? reason.message
            : isTestingRefusal(reason)
              ? t("assistant.refusal.testing")
              : t(REFUSAL_TEXTS[reason.code]);
        const fix = reason.code !== null && reason.code in fixLinks ? fixLinks[reason.code as GoLiveCheckCode] : undefined;
        return (
          <li key={`${reason.code ?? "other"}-${index}`} className="flex items-start gap-3">
            <IconXCircle className="mt-0.5 size-5 shrink-0 text-danger" aria-hidden />
            <div className="min-w-0 flex-1 text-sm text-ink">
              <p>{text}</p>
              {reason.code === "profile_gaps" && reason.details.length > 0 ? (
                <div className="text-ink-muted">
                  <GapList kinds={reason.details} />
                </div>
              ) : null}
              {fix ? (
                <div className="mt-1">
                  <FixLink href={fix.href}>{t(fix.label)}</FixLink>
                </div>
              ) : null}
              {reason.code === "autotests" && !isTestingRefusal(reason) && onRunAutotests ? (
                <div className="mt-1">
                  <ActionButton onClick={onRunAutotests}>{t("assistant.autotests.run")}</ActionButton>
                </div>
              ) : null}
            </div>
          </li>
        );
      })}
    </ul>
  );
}

"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { api } from "@/api/client";
import { useApiQuery } from "@/api/hooks";
import type { Schema } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconCheckCircle, IconXCircle } from "@/components/content/icons";
import { IconAlert, IconClock } from "@/components/icons";
import { Card, Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import type { AssistantVersionStatus, PublishRefusal, PublishRefusalReason } from "@/lib/assistant";
import { cn } from "@/lib/cn";
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

type CheckState = "ok" | "missing" | "pending" | "unknown";

function CheckRow({ state, title, detail, action }: { state: CheckState; title: string; detail?: ReactNode; action?: ReactNode }) {
  const { t } = useI18n();
  const icon =
    state === "ok" ? (
      <IconCheckCircle className="size-5 text-success" aria-hidden />
    ) : state === "missing" ? (
      <IconXCircle className="size-5 text-danger" aria-hidden />
    ) : state === "pending" ? (
      <IconClock className="size-5 text-info" aria-hidden />
    ) : (
      <IconAlert className="size-5 text-ink-subtle" aria-hidden />
    );
  const stateLabel: Record<CheckState, MessageKey> = {
    ok: "assistant.checklist.state.ok",
    missing: "assistant.checklist.state.missing",
    pending: "assistant.checklist.state.pending",
    unknown: "assistant.checklist.state.unknown",
  };
  return (
    <li className="flex items-start gap-3 py-3">
      <span className="mt-0.5 shrink-0">{icon}</span>
      <div className="min-w-0 flex-1">
        <p className={cn("text-sm font-medium", state === "ok" ? "text-ink" : "text-ink")}>
          {title}
          <span className="sr-only">: {t(stateLabel[state])}</span>
        </p>
        {detail ? <div className="mt-0.5 text-sm text-ink-muted">{detail}</div> : null}
      </div>
      {action ? <div className="shrink-0 self-center">{action}</div> : null}
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

/**
 * What must be true before customers get this version (concept: the trial
 * or a paid plan, the data processing agreement, a complete profile and
 * passed autotests), each with a link to fix it.
 */
export function GoLiveChecklist({
  status,
  onRunAutotests,
  canRunAutotests,
}: {
  status: AssistantVersionStatus;
  onRunAutotests: () => void;
  canRunAutotests: boolean;
}) {
  const { t, tp, locale } = useI18n();
  const { business } = useBusiness();

  const gaps = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/profile/gaps", {
        params: { path: { business_id: business.id }, query: { language: locale } },
      }),
    [business.id, locale],
  );
  const dpa = useApiQuery(
    () => api.GET("/v1/businesses/{business_id}/dpa", { params: { path: { business_id: business.id } } }),
    [business.id],
  );
  const billing = useApiQuery(
    () => api.GET("/v1/businesses/{business_id}/billing", { params: { path: { business_id: business.id } } }),
    [business.id],
  );

  const blocking = (gaps.data?.gaps ?? []).filter((gap) => gap.is_blocking);
  const subscription = billing.data?.subscription ?? null;
  const subscriptionState: CheckState = billing.data
    ? subscription && (subscription.status === "trialing" || subscription.status === "active")
      ? "ok"
      : "missing"
    : billing.error
      ? "unknown"
      : "pending";

  const loading = <Spinner size="sm" label={t("common.loading")} />;

  return (
    <Card title={t("assistant.checklist.title")} description={t("assistant.checklist.description")}>
      <ul className="-my-3 divide-y divide-line">
        <CheckRow
          state={status === "ready" ? "ok" : status === "testing" ? "pending" : "missing"}
          title={t("assistant.checklist.autotests")}
          detail={
            status === "ready"
              ? t("assistant.checklist.autotestsOk")
              : status === "testing"
                ? t("assistant.checklist.autotestsRunning")
                : t("assistant.checklist.autotestsMissing")
          }
          action={
            canRunAutotests && status !== "ready" && status !== "testing" ? (
              <button type="button" onClick={onRunAutotests} className="text-sm font-medium whitespace-nowrap text-accent hover:underline">
                {t("assistant.autotests.run")}
              </button>
            ) : undefined
          }
        />
        <CheckRow
          state={gaps.data ? (blocking.length === 0 ? "ok" : "missing") : gaps.error ? "unknown" : "pending"}
          title={t("assistant.checklist.profile")}
          detail={
            gaps.data
              ? blocking.length === 0
                ? t("assistant.checklist.profileOk")
                : tp("onboarding.gaps.notReady", blocking.length)
              : gaps.error
                ? t("assistant.checklist.unknown")
                : loading
          }
          action={blocking.length > 0 ? <FixLink href={businessPath(business.id, "onboarding")}>{t("assistant.checklist.fixProfile")}</FixLink> : undefined}
        />
        <CheckRow
          state={dpa.data ? (dpa.data.is_current_version_accepted ? "ok" : "missing") : dpa.error ? "unknown" : "pending"}
          title={t("assistant.checklist.dpa")}
          detail={
            dpa.data
              ? dpa.data.is_current_version_accepted
                ? t("assistant.checklist.dpaOk")
                : t("assistant.checklist.dpaMissing", { version: dpa.data.current_document_version })
              : dpa.error
                ? t("assistant.checklist.unknown")
                : loading
          }
          action={
            dpa.data && !dpa.data.is_current_version_accepted ? (
              <FixLink href={businessPath(business.id, "settings")}>{t("assistant.checklist.fixDpa")}</FixLink>
            ) : undefined
          }
        />
        <CheckRow
          state={subscriptionState}
          title={t("assistant.checklist.billing")}
          detail={
            billing.data
              ? subscriptionState === "ok"
                ? subscription?.status === "trialing"
                  ? t("assistant.checklist.billingTrial")
                  : t("assistant.checklist.billingActive")
                : billing.data.is_trial_available
                  ? t("assistant.checklist.billingStartTrial")
                  : t("assistant.checklist.billingMissing")
              : billing.error
                ? t("assistant.checklist.unknown")
                : loading
          }
          action={
            subscriptionState === "missing" ? (
              <FixLink href={businessPath(business.id, "billing")}>{t("assistant.checklist.fixBilling")}</FixLink>
            ) : undefined
          }
        />
      </ul>
    </Card>
  );
}

const REASON_TEXTS: Record<PublishRefusalReason, MessageKey> = {
  subscription: "assistant.refusal.subscription",
  dpa: "assistant.refusal.dpa",
  profile: "assistant.refusal.profile",
  autotests: "assistant.refusal.autotests",
  testing: "assistant.refusal.testing",
  alreadyLive: "assistant.refusal.alreadyLive",
  archived: "assistant.refusal.archived",
  notArchived: "assistant.refusal.notArchived",
  adminOnly: "assistant.refusal.adminOnly",
};

/** Why publishing (or rolling back) was refused, with links to fix each reason. */
export function RefusalReasons({
  refusal,
  detail,
  onRunAutotests,
}: {
  refusal: PublishRefusal;
  /** The API's own message, shown when no reason was recognized. */
  detail: string | null;
  onRunAutotests?: () => void;
}) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const links: Partial<Record<PublishRefusalReason, ReactNode>> = {
    subscription: <FixLink href={businessPath(business.id, "billing")}>{t("assistant.checklist.fixBilling")}</FixLink>,
    dpa: <FixLink href={businessPath(business.id, "settings")}>{t("assistant.checklist.fixDpa")}</FixLink>,
    profile: <FixLink href={businessPath(business.id, "onboarding")}>{t("assistant.checklist.fixProfile")}</FixLink>,
    autotests: onRunAutotests ? (
      <button type="button" onClick={onRunAutotests} className="text-sm font-medium whitespace-nowrap text-accent hover:underline">
        {t("assistant.autotests.run")}
      </button>
    ) : undefined,
  };

  if (refusal.reasons.length === 0) {
    return <p className="text-sm text-ink-muted">{detail ?? t("errors.codes.conflict")}</p>;
  }

  return (
    <ul className="space-y-3">
      {refusal.reasons.map((reason) => (
        <li key={reason} className="flex items-start gap-3">
          <IconXCircle className="mt-0.5 size-5 shrink-0 text-danger" aria-hidden />
          <div className="min-w-0 flex-1 text-sm text-ink">
            <p>{t(REASON_TEXTS[reason])}</p>
            {reason === "profile" && refusal.gapKinds.length > 0 ? (
              <ul className="mt-1 list-disc pl-5 text-ink-muted">
                {refusal.gapKinds.map((kind) => (
                  <li key={kind}>{isGapKind(kind) ? t(GAP_KIND_LABELS[kind]) : kind}</li>
                ))}
              </ul>
            ) : null}
          </div>
          {links[reason] ? <div className="shrink-0">{links[reason]}</div> : null}
        </li>
      ))}
    </ul>
  );
}

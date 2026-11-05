"use client";

import { useEffect, useRef, type ReactNode } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { Card, ErrorState, LoadingRegion, SkeletonText } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { blockingChecks, checkState, type GoLiveCheckCode } from "@/lib/assistant/goLive";

import { CheckDetail } from "./CheckDetail";
import { CheckRow } from "./CheckRow";
import { ActionButton, FixLink, useFixLinks } from "./goLiveFixes";

const CHECK_TITLES: Record<GoLiveCheckCode, MessageKey> = {
  subscription_or_trial: "assistant.checklist.billing",
  dpa: "assistant.checklist.dpa",
  profile_gaps: "assistant.checklist.profile",
  staff_contact: "assistant.checklist.staffContact",
  autotests: "assistant.checklist.autotests",
  voice_configuration: "assistant.checklist.voice",
};

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

  // Depends on everything the go-live checks read: always asked again when shown.
  const readiness = useQuery(
    queryKeys.assistant.readiness(business.id, versionId),
    () =>
      api.GET("/v1/businesses/{business_id}/assistant-versions/{version_id}/go-live-readiness", {
        params: { path: { business_id: business.id, version_id: versionId } },
      }),
    { staleMs: 0 },
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
    body = (
      <LoadingRegion label={t("common.loading")}>
        <SkeletonText lines={5} />
      </LoadingRegion>
    );
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

"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { Alert, ButtonLink, Checkbox, ConfirmDialog, Spinner, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

/**
 * "Build a new version": the assistant is assembled from the current
 * profile, knowledge and resources, then (by default) autotested.
 */
export function BuildVersionDialog({ onClose, onBuilt }: { onClose: () => void; onBuilt: () => void }) {
  const { t, tp, locale } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { business, isSetUp, markSetUp } = useBusiness();
  const [runAutotests, setRunAutotests] = useState(true);

  const gaps = useQuery(
    queryKeys.profile.gaps(business.id, locale),
    () =>
      api.GET("/v1/businesses/{business_id}/profile/gaps", {
        params: { path: { business_id: business.id }, query: { language: locale } },
      }),
    { staleMs: 0 },
  );
  const build = useMutation(
    (run: boolean) =>
      api.POST("/v1/businesses/{business_id}/assistant-versions", {
        params: { path: { business_id: business.id } },
        body: { run_autotests: run },
      }),
    { invalidate: [queryKeys.assistant.all(business.id)], stale: [queryKeys.dashboard.all(business.id)] },
  );

  const blocking = (gaps.data?.gaps ?? []).filter((gap) => gap.is_blocking);

  const submit = async () => {
    const result = await build.run(runAutotests);
    if (!result.ok) {
      return;
    }
    toast.success(t("assistant.build.built", { number: result.data.version_number }));
    onBuilt();
    if (!isSetUp) {
      // The first version: the assistant exists, the cabinet's sections open now.
      markSetUp();
    }
    router.push(`${businessPath(business.id, "assistant")}/versions/${encodeURIComponent(result.data.id)}`);
    // The business moves from "filling in the profile" to "testing".
    router.refresh();
  };

  return (
    <ConfirmDialog
      open
      tone="primary"
      title={t("assistant.build.title")}
      description={t("assistant.build.description")}
      confirmLabel={t("assistant.build.confirm")}
      pendingLabel={runAutotests ? t("assistant.build.buildingAndTesting") : t("assistant.build.building")}
      isPending={build.isPending}
      onConfirm={() => void submit()}
      onClose={onClose}
    >
      {gaps.isLoading && !gaps.data ? (
        <p className="flex items-center gap-2">
          <Spinner size="sm" /> {t("assistant.build.checkingProfile")}
        </p>
      ) : blocking.length > 0 ? (
        <Alert
          tone="warning"
          title={tp("onboarding.gaps.notReady", blocking.length)}
          action={
            <ButtonLink href={businessPath(business.id, "assistant/profile")} size="sm" variant="secondary">
              {t("assistant.build.openProfile")}
            </ButtonLink>
          }
        >
          {t("assistant.build.gapsHint")}
        </Alert>
      ) : null}
      <Checkbox
        id="build-run-autotests"
        label={t("assistant.build.runAutotests")}
        description={t("assistant.build.runAutotestsHint")}
        checked={runAutotests}
        onChange={(event) => setRunAutotests(event.target.checked)}
      />
    </ConfirmDialog>
  );
}

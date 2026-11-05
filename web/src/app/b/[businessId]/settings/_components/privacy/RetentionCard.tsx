"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { Card, ErrorState, LoadingRegion, SkeletonRows } from "@/components/ui";
import { OwnerOnlyState } from "@/components/workspace/OwnerOnly";
import { useI18n } from "@/i18n/client";

import { usePrivacySettings } from "../../_lib/usePrivacySettings";
import { RetentionForm } from "./RetentionForm";

/**
 * Settings → Privacy → "How long data is kept": the owner's retention
 * periods, the latest nightly cleanup, the sub-processors whose copies
 * go too, and whether real conversations join the nightly quality sample,
 * all saved as they are chosen. Owners only: staff see why not.
 */
export function RetentionCard() {
  const { t } = useI18n();
  const { isOwner } = useBusiness();
  const state = usePrivacySettings({ enabled: isOwner });
  const { settings } = state;

  if (!isOwner || settings.error?.code === "access_denied") {
    return (
      <Card title={t("privacyRetention.title")}>
        <OwnerOnlyState className="py-4" />
      </Card>
    );
  }

  return (
    <Card title={t("privacyRetention.title")} description={t("privacyRetention.description")}>
      {settings.error && !settings.data ? (
        <ErrorState error={settings.error} onRetry={settings.reload} className="py-4" />
      ) : !settings.data ? (
        <LoadingRegion label={t("common.loading")}>
          <SkeletonRows rows={3} />
        </LoadingRegion>
      ) : (
        <RetentionForm stored={settings.data} state={state} />
      )}
    </Card>
  );
}

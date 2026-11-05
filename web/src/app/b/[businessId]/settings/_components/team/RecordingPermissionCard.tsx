"use client";

/**
 * Settings → Team: whether staff may play the call recordings (off by
 * default: owners only). Owners switch it (a recent sign-in or
 * confirmation, like every team change); it takes effect at staff's next
 * playback.
 */

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { Card, Checkbox, InlineError, Skeleton, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

export function RecordingPermissionCard() {
  const { t } = useI18n();
  const toast = useToast();
  const { business, isOwner } = useBusiness();
  const path = { business_id: business.id };
  const security = useQuery(queryKeys.settings.security(business.id), () =>
    api.GET("/v1/businesses/{business_id}/security", { params: { path } }),
  );
  const save = useMutation((allowed: boolean) =>
    api.PUT("/v1/businesses/{business_id}/security", {
      params: { path },
      body: { staff_may_play_recordings: allowed },
    }),
  );
  const view = security.data;

  const toggle = async (allowed: boolean) => {
    const result = await save.run(allowed);
    if (result.ok) {
      security.setData(result.data);
      toast.success(t("security.recordings.saved"));
    }
  };

  return (
    <Card title={t("security.recordings.title")} description={t("security.recordings.description")}>
      {view ? (
        <div className="space-y-3">
          <Checkbox
            label={t("security.recordings.toggle")}
            description={view.staff_may_play_recordings ? t("security.recordings.on") : t("security.recordings.off")}
            checked={view.staff_may_play_recordings}
            disabled={!isOwner || save.isPending}
            onChange={(event) => void toggle(event.target.checked)}
          />
          {!isOwner ? <p className="text-sm text-ink-subtle">{t("security.team.ownerOnly")}</p> : null}
        </div>
      ) : security.error ? (
        <InlineError error={security.error} />
      ) : (
        <Skeleton className="h-16 w-full" />
      )}
    </Card>
  );
}

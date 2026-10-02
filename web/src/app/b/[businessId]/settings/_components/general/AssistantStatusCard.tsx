"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { useMutation } from "@/api/useMutation";
import { BusinessStatusBadge } from "@/components/business/BusinessStatusBadge";
import { useBusiness } from "@/components/business/BusinessContext";
import { Alert, Badge, Button, ButtonLink, Card, useToast } from "@/components/ui";
import { ConfirmDialog } from "@/components/ui";
import { IconPause, IconPlay } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import type { BusinessView } from "../../_lib/general";

/** The assistant's live/paused switch (only the status is sent) and the service mode. */
export function AssistantStatusCard({ onSaved }: { onSaved: (business: BusinessView) => void }) {
  const { t } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { business, isOwner } = useBusiness();
  const [isConfirmingPause, setConfirmingPause] = useState(false);
  const [pauseError, setPauseError] = useState<ApiError | null>(null);
  const [status, setStatus] = useState(business.status);
  const switchStatus = useMutation(
    (next: "live" | "paused") =>
      api.PATCH("/v1/businesses/{business_id}", { params: { path: { business_id: business.id } }, body: { status: next } }),
    { errorToast: false },
  );

  const run = async (next: "live" | "paused") => {
    // Only the status is sent: pausing or resuming overwrites no other setting.
    const result = await switchStatus.run(next);
    if (result.ok) {
      setStatus(result.data.status);
      onSaved(result.data);
      setConfirmingPause(false);
      router.refresh();
      toast.success(t(next === "paused" ? "settings.status.pausedToast" : "settings.status.resumedToast"));
    } else if (next === "paused") {
      setPauseError(result.error);
    } else {
      toast.error(result.error);
    }
  };

  const description =
    status === "live" ? t("settings.status.live") : status === "paused" ? t("settings.status.paused") : t("settings.status.notLive");

  return (
    <Card
      title={t("settings.status.title")}
      actions={<BusinessStatusBadge status={status} />}
      footer={
        isOwner && (status === "live" || status === "paused") ? (
          status === "live" ? (
            <Button
              variant="secondary"
              leadingIcon={<IconPause className="size-4" aria-hidden />}
              onClick={() => {
                setPauseError(null);
                setConfirmingPause(true);
              }}
            >
              {t("settings.status.pause")}
            </Button>
          ) : (
            <Button leadingIcon={<IconPlay className="size-4" aria-hidden />} isLoading={switchStatus.isPending} onClick={() => run("live")}>
              {t("settings.status.resume")}
            </Button>
          )
        ) : status === "onboarding" || status === "testing" ? (
          <ButtonLink href={businessPath(business.id, "assistant")} variant="secondary">
            {t("settings.status.openAssistant")}
          </ButtonLink>
        ) : undefined
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-ink-muted">{description}</p>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-ink-subtle">{t("settings.status.serviceMode")}:</span>
          <Badge tone={business.service_mode === "full" ? "success" : "danger"}>
            {t(business.service_mode === "full" ? "billing.serviceModes.full" : "billing.serviceModes.leads_only")}
          </Badge>
        </div>
        {business.service_mode === "leads_only" ? (
          <Alert tone="warning">
            <p>{t("settings.status.leadsOnlyHint")}</p>
            <ButtonLink href={businessPath(business.id, "settings/billing")} size="sm" variant="secondary" className="mt-3">
              {t("channels.openBilling")}
            </ButtonLink>
          </Alert>
        ) : null}
      </div>
      <ConfirmDialog
        open={isConfirmingPause}
        onClose={() => setConfirmingPause(false)}
        onConfirm={() => run("paused")}
        isPending={switchStatus.isPending}
        error={pauseError}
        title={t("settings.status.pauseTitle")}
        description={t("settings.status.pauseDescription")}
        confirmLabel={t("settings.status.pause")}
      />
    </Card>
  );
}

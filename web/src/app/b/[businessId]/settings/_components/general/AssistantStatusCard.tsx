"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/api/client";
import { useMutation } from "@/api/useMutation";
import { BusinessStatusBadge } from "@/components/business/BusinessStatusBadge";
import { useBusiness } from "@/components/business/BusinessContext";
import { Alert, Badge, Button, ButtonLink, Card, useToast } from "@/components/ui";
import { IconPause, IconPlay } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import type { BusinessView } from "../../_lib/general";

/**
 * The assistant's live/paused switch (only the status is sent) and the
 * service mode. Pausing takes effect at once and offers Undo for a few
 * seconds, like every other setting on the page; resuming is one press.
 */
export function AssistantStatusCard({ onSaved }: { onSaved: (business: BusinessView) => void }) {
  const { t } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { business, isOwner } = useBusiness();
  const [status, setStatus] = useState(business.status);
  const switchStatus = useMutation(
    (next: "live" | "paused") =>
      api.PATCH("/v1/businesses/{business_id}", { params: { path: { business_id: business.id } }, body: { status: next } }),
  );

  const run = async (next: "live" | "paused", offerUndo: boolean) => {
    // Only the status is sent: pausing or resuming overwrites no other setting.
    const result = await switchStatus.run(next);
    if (!result.ok) {
      return;
    }
    setStatus(result.data.status);
    onSaved(result.data);
    router.refresh();
    const title = t(next === "paused" ? "settings.status.pausedToast" : "settings.status.resumedToast");
    if (offerUndo) {
      toast.undoable(title, () => void run(next === "paused" ? "live" : "paused", false));
    } else {
      toast.success(title);
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
              isLoading={switchStatus.isPending}
              onClick={() => void run("paused", true)}
            >
              {t("settings.status.pause")}
            </Button>
          ) : (
            <Button
              leadingIcon={<IconPlay className="size-4" aria-hidden />}
              isLoading={switchStatus.isPending}
              onClick={() => void run("live", false)}
            >
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
    </Card>
  );
}

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { useBusinessClosure } from "@/components/business/useBusinessClosure";
import { IconDownload } from "@/components/icons";
import { Button, Card, ConfirmDialog, UserSentence, buttonClasses, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { closureCountdown, type ClosureCountdown } from "@/lib/closure";
import { businessPath } from "@/lib/navigation";

const CONSEQUENCES = ["closure.zone.willPause", "closure.zone.willStopCharges", "closure.zone.willDelete", "closure.zone.willKeep"] as const;

/**
 * Settings → Business, the danger zone (owners): closing the business, with
 * its name typed to confirm and a recent sign-in (the step-up dialog asks
 * when needed); while it closes, the day it is deleted, who closed it and
 * keeping it; once the deletion has begun, only that. The full export is
 * offered at every step, in Settings → Privacy.
 */
export function CloseBusinessCard() {
  const { t } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { business, isOwner } = useBusiness();
  const { closure, keep, isKeeping } = useBusinessClosure();
  const [isConfirming, setConfirming] = useState(false);
  const [openedAt] = useState(() => Date.now());
  const close = useMutation(
    () =>
      api.POST("/v1/businesses/{business_id}/closure", {
        params: { path: { business_id: business.id } },
        body: { confirmation_name: business.name },
      }),
    { errorToast: false, invalidate: [queryKeys.closure.detail(business.id), queryKeys.business.all(business.id)] },
  );

  const view = closure.data;
  if (!isOwner || view === undefined) {
    return null;
  }
  const exportLink = (
    <Link href={businessPath(business.id, "settings/privacy")} className={buttonClasses({ variant: "secondary", size: "sm" })}>
      <IconDownload className="size-4" aria-hidden />
      {t("closure.zone.export")}
    </Link>
  );

  const onClose = async () => {
    const result = await close.run();
    if (!result.ok) {
      return;
    }
    closure.setData(result.data);
    setConfirming(false);
    toast.success(t("closure.zone.closed"));
    router.refresh();
  };

  if (view.state === "deleting") {
    return (
      <Card title={t("closure.zone.deletingTitle")} className="border-danger/40" data-testid="close-business">
        <p className="text-sm text-ink-muted">{t("closure.zone.deletingDescription")}</p>
      </Card>
    );
  }
  const countdown = closureCountdown(view, openedAt);
  if (countdown) {
    return (
      <Card title={t("closure.zone.pendingTitle")} className="border-danger/40" data-testid="close-business">
        <ClosingFacts countdown={countdown} />
        <div className="mt-4 flex flex-wrap gap-2">
          {countdown.canCancel ? (
            <Button size="sm" isLoading={isKeeping} onClick={() => void keep()}>
              {t("closure.zone.keep")}
            </Button>
          ) : countdown.isUnpaid ? (
            <Link href={businessPath(business.id, "settings/billing")} className={buttonClasses({ size: "sm" })}>
              {t("closure.zone.billing")}
            </Link>
          ) : null}
          {exportLink}
        </div>
      </Card>
    );
  }

  return (
    <Card
      title={t("closure.zone.title")}
      description={t("closure.zone.description")}
      className="border-danger/40"
      data-testid="close-business"
    >
      <ul className="list-disc space-y-1.5 ps-5 text-sm text-ink-muted marker:text-ink-subtle">
        {CONSEQUENCES.map((key) => (
          <li key={key}>{t(key)}</li>
        ))}
      </ul>
      <p className="mt-4 text-sm text-ink">{t("closure.zone.exportFirst")}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {exportLink}
        <Button variant="danger" size="sm" onClick={() => setConfirming(true)} aria-haspopup="dialog">
          {t("closure.zone.action")}
        </Button>
      </div>
      <ConfirmDialog
        open={isConfirming}
        onClose={() => setConfirming(false)}
        onConfirm={onClose}
        title={t("closure.zone.dialogTitle")}
        description={t("closure.zone.dialogDescription")}
        confirmLabel={t("closure.zone.confirm")}
        pendingLabel={t("closure.zone.closing")}
        confirmationText={business.name}
        isPending={close.isPending}
        error={close.error}
      />
    </Card>
  );
}

/** When the business is deleted, who closed it and why, and what keeping it does. */
function ClosingFacts({ countdown }: { countdown: ClosureCountdown }) {
  const { t, tp } = useI18n();
  const format = useBusinessFormat();
  const closedOn = format.date(countdown.requestedAt);

  return (
    <div className="space-y-1.5 text-sm">
      <p className="font-medium text-ink">
        {countdown.daysLeft > 0
          ? tp("closure.banner.countdown", countdown.daysLeft, {
              count: String(countdown.daysLeft),
              date: format.date(countdown.deleteAfter),
            })
          : t("closure.banner.due")}
      </p>
      <p className="text-ink-muted">
        {countdown.actorName ? (
          <UserSentence text={t("closure.zone.closedBy", { date: closedOn })} values={{ name: countdown.actorName }} />
        ) : (
          t("closure.zone.closedOn", { date: closedOn })
        )}
      </p>
      <p className="text-ink-muted">
        {countdown.isUnpaid && !countdown.canCancel ? t("closure.zone.unpaidHint") : t("closure.zone.keepHint")}
      </p>
    </div>
  );
}

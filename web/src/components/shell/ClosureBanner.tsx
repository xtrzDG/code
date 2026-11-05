"use client";

/**
 * Over the cabinet of a closing business, for its whole team: the day it
 * is deleted for good and the days left, why (closed for non-payment), and
 * for an owner "Keep the business" (or, when it was closed for
 * non-payment and is not paid yet, Billing) and the closing details in
 * Settings → Business. Once the deletion has begun it only says so. Not
 * shown on Settings → Business, whose danger zone says the same; on a
 * phone it keeps to its title, the countdown and the actions.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useId, useState } from "react";

import { IconClock } from "@/components/icons";
import { Button, buttonClasses } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { closureCountdown } from "@/lib/closure";
import { businessPath } from "@/lib/navigation";

import { useBusiness, useBusinessFormat } from "../business/BusinessContext";
import { useBusinessClosure } from "../business/useBusinessClosure";

export function ClosureBanner() {
  const { t, tp } = useI18n();
  const { business, isOwner } = useBusiness();
  const format = useBusinessFormat();
  const pathname = usePathname();
  const titleId = useId();
  const { closure, keep, isKeeping } = useBusinessClosure();
  const settingsPath = businessPath(business.id, "settings");
  // The moment the page opened: the countdown counts whole days.
  const [openedAt] = useState(() => Date.now());
  const view = closure.data;
  const countdown = closureCountdown(view, openedAt);

  if (pathname === settingsPath || (countdown === null && view?.state !== "deleting")) {
    return null;
  }
  const isDeleting = countdown === null;
  return (
    <section
      aria-labelledby={titleId}
      data-testid="closure-banner"
      data-shell-banner=""
      className="mb-3 flex flex-wrap items-start gap-x-3 gap-y-2 rounded-2xl border border-danger/40 bg-danger-soft/60 px-4 py-2.5 text-sm sm:mb-5 sm:gap-y-3 sm:py-3"
    >
      <IconClock className="mt-0.5 size-5 shrink-0 text-danger" aria-hidden />
      <div className="min-w-0 flex-1 basis-60 space-y-1">
        <p id={titleId} className="font-medium text-ink">
          {t("closure.banner.title")}
        </p>
        <p className="text-ink-muted">
          {isDeleting
            ? t("closure.banner.deleting")
            : countdown.daysLeft > 0
              ? tp("closure.banner.countdown", countdown.daysLeft, {
                  count: String(countdown.daysLeft),
                  date: format.date(countdown.deleteAfter),
                })
              : t("closure.banner.due")}
        </p>
        {countdown?.isUnpaid ? <p className="hidden text-ink-muted sm:block">{t("closure.banner.unpaid")}</p> : null}
      </div>
      {countdown && isOwner ? (
        <div className="flex shrink-0 flex-wrap gap-2">
          {countdown.canCancel ? (
            <Button size="sm" isLoading={isKeeping} onClick={() => void keep()}>
              {t("closure.banner.keep")}
            </Button>
          ) : countdown.isUnpaid ? (
            <Link href={businessPath(business.id, "settings/billing")} className={buttonClasses({ size: "sm" })}>
              {t("closure.banner.pay")}
            </Link>
          ) : null}
          <Link href={settingsPath} className={buttonClasses({ variant: "ghost", size: "sm" })}>
            {t("closure.banner.open")}
          </Link>
        </div>
      ) : null}
    </section>
  );
}

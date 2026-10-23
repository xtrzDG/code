"use client";

/**
 * Over an owner's cabinet once the business is live and the owner signs in
 * with a login code alone: turn on a second factor (a passkey or an
 * authenticator app) in Account → Security, or put the reminder away. Put
 * away, it comes back when the team grows past the owner. Hidden for staff
 * and once the owner has a second factor.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useId } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { IconShield } from "@/components/icons";
import { Button, buttonClasses } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { securityPath } from "@/lib/navigation";

import { useBusiness } from "../business/BusinessContext";

export function SecurityNudgeBanner() {
  const { t } = useI18n();
  const { business, isOwner } = useBusiness();
  const pathname = usePathname();
  const titleId = useId();
  const path = { business_id: business.id };
  const nudge = useQuery(
    queryKeys.securityNudge.detail(business.id),
    () => api.GET("/v1/businesses/{business_id}/security-nudge", { params: { path } }),
    { enabled: isOwner },
  );
  const putAway = useMutation(
    () => api.PUT("/v1/businesses/{business_id}/security-nudge/dismissal", { params: { path } }),
    { invalidate: [queryKeys.securityNudge.detail(business.id), queryKeys.setup.all(business.id)] },
  );

  if (!isOwner || !nudge.data?.is_shown) {
    return null;
  }
  return (
    <section
      aria-label={t("securityNudge.title")}
      data-testid="security-nudge"
      data-shell-banner=""
      className="mb-5 flex flex-wrap items-start gap-3 rounded-2xl border border-accent/30 bg-accent-soft/50 px-4 py-3 text-sm"
    >
      <IconShield className="mt-0.5 size-5 shrink-0 text-accent" aria-hidden />
      <div className="min-w-0 flex-1 basis-60 space-y-1">
        <p id={titleId} className="font-medium text-ink">
          {t("securityNudge.title")}
        </p>
        <p className="text-ink-muted">
          {t(nudge.data.reason === "team_grew" ? "securityNudge.teamGrew" : "securityNudge.description")}
        </p>
      </div>
      <div className="flex shrink-0 flex-wrap gap-2">
        <Link href={securityPath({ next: pathname })} className={buttonClasses({ size: "sm" })}>
          {t("securityNudge.action")}
        </Link>
        <Button
          variant="ghost"
          size="sm"
          // Named by its visible words (WCAG 2.5.3); the title says what it hides.
          aria-describedby={titleId}
          isLoading={putAway.isPending}
          onClick={() => void putAway.run()}
        >
          {t("securityNudge.dismiss")}
        </Button>
      </div>
    </section>
  );
}

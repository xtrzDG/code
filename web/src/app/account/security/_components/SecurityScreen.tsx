"use client";

/**
 * Account → Security: the authenticator app, recovery codes, this
 * session and every signed-in device. The page keeps the latest `GET /v1/me/security` and
 * reads it again after every change; each card does its own requests
 * (sensitive ones may first ask to confirm with a code: the step-up dialog
 * is global).
 */

import Link from "next/link";
import { useState } from "react";

import { api } from "@/api/client";
import { unwrap } from "@/api/result";
import type { AccountSecurityView, CurrentUserView } from "@/api/types";
import { IconArrowLeft } from "@/components/icons";
import { Alert, ButtonLink, PageHeader } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { HOME_PATH, type SecurityReason } from "@/lib/navigation";

import { AuthenticatorCard } from "./AuthenticatorCard";
import { DevicesCard } from "./DevicesCard";
import { RecoveryCodesCard } from "./RecoveryCodesCard";
import { SessionCard } from "./SessionCard";

export function SecurityScreen({
  me,
  initial,
  reason,
  next,
}: {
  me: CurrentUserView;
  initial: AccountSecurityView;
  reason: SecurityReason | null;
  next: string | null;
}) {
  const { t } = useI18n();
  const [security, setSecurity] = useState(initial);
  const account = me.user.email ?? me.user.phone_number ?? "";

  const refresh = async () => {
    setSecurity(await unwrap(api.GET("/v1/me/security")));
  };

  const isTwoFactor = security.auth_level === "two_factor";
  const isActive = security.totp_status === "active";

  return (
    <div className="space-y-6">
      <Link
        href={HOME_PATH}
        className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-muted hover:text-ink"
      >
        <IconArrowLeft className="size-4 rtl:-scale-x-100" aria-hidden />
        {t("security.back")}
      </Link>
      <PageHeader
        title={t("security.title")}
        description={t("security.description")}
      />
      {reason ? (
        <Alert tone={isTwoFactor ? "success" : "warning"}>
          <p>
            {t(
              reason === "admin"
                ? "security.required.admin"
                : "security.required.business",
            )}
          </p>
          {isTwoFactor && next ? (
            <ButtonLink href={next} size="sm" className="mt-3">
              {t("security.required.continue")}
            </ButtonLink>
          ) : null}
        </Alert>
      ) : null}
      <AuthenticatorCard
        security={security}
        account={account}
        onChanged={refresh}
      />
      {isActive ? (
        <RecoveryCodesCard
          left={security.recovery_codes_left ?? 0}
          account={account}
          onChanged={refresh}
        />
      ) : null}
      <SessionCard security={security} onChanged={refresh} />
      <DevicesCard isPlatformAdmin={me.user.is_platform_admin} />
    </div>
  );
}

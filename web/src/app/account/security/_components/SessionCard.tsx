"use client";

/**
 * How this session is signed in. With a second factor set up (the
 * authenticator app or a passkey) but a session from the login code alone
 * (an older sign-in), confirming with it counts the session as two-factor
 * (the step-up dialog: the app's code, a passkey or a recovery code).
 */

import { useState } from "react";

import { requestStepUp } from "@/api/stepUp";
import type { AccountSecurityView } from "@/api/types";
import { Button, Card, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

export function SessionCard({
  security,
  onChanged,
}: {
  security: AccountSecurityView;
  onChanged: () => Promise<void>;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const [isConfirming, setConfirming] = useState(false);
  const isTwoFactor = security.auth_level === "two_factor";
  const hasSecondFactor =
    security.totp_status === "active" || security.passkey_count > 0;
  const canUpgrade = !isTwoFactor && hasSecondFactor;

  const upgrade = async () => {
    setConfirming(true);
    try {
      if (await requestStepUp()) {
        await onChanged();
        toast.success(t("security.session.upgraded"));
      }
    } finally {
      setConfirming(false);
    }
  };

  return (
    <Card title={t("security.session.title")}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink">
          {isTwoFactor
            ? t("security.session.twoFactor")
            : t("security.session.oneFactor")}
        </p>
        {canUpgrade ? (
          <Button
            variant="secondary"
            isLoading={isConfirming}
            onClick={() => void upgrade()}
          >
            {t("security.session.upgrade")}
          </Button>
        ) : null}
      </div>
    </Card>
  );
}

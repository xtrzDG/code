"use client";

/**
 * Account → Security, the danger zone: deleting one's own account, with
 * the account's email or phone typed to confirm and a recent sign-in (the
 * step-up dialog asks when needed). Refused while the person is the last
 * owner of a business that is not closing or the only owner of a brand:
 * the card then names them (from the person's memberships) and says what
 * to do first. Members of the platform team leave the team first. Once
 * deleted, the session's cookie goes and the sign-in page opens.
 */

import { useState } from "react";

import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { useMutation } from "@/api/useMutation";
import type { CurrentUserView } from "@/api/types";
import { Alert, Button, Card, ConfirmDialog, UserSentence } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { LAST_BRAND_OWNER, LAST_BUSINESS_OWNER, PLATFORM_TEAM, refusedNames } from "@/lib/closure";
import { listFormat } from "@/lib/intl/formatters";
import { LOGIN_PATH } from "@/lib/navigation";

interface Refusal {
  text: string;
  names: string | null;
}

export function DeleteAccountCard({ me, account }: { me: CurrentUserView; account: string }) {
  const { t, locale } = useI18n();
  const [isConfirming, setConfirming] = useState(false);
  const [refusal, setRefusal] = useState<Refusal | null>(null);
  const remove = useMutation(() => api.DELETE("/v1/me"), { errorToast: false });

  const refusalOf = (error: ApiError): Refusal | null => {
    for (const reason of error.reasons) {
      if (reason.code === PLATFORM_TEAM) {
        return { text: t("closure.account.platformTeam"), names: null };
      }
      if (reason.code === LAST_BUSINESS_OWNER || reason.code === LAST_BRAND_OWNER) {
        const names = refusedNames(reason, me.memberships ?? []);
        if (names.length === 0) {
          return { text: t("closure.account.lastOwnerUnnamed"), names: null };
        }
        const key = reason.code === LAST_BUSINESS_OWNER ? "closure.account.lastOwner" : "closure.account.lastBrandOwner";
        return { text: t(key), names: listFormat(locale, { type: "conjunction" }).format(names) };
      }
    }
    return null;
  };

  const onDelete = async () => {
    const result = await remove.run();
    if (!result.ok) {
      const refused = refusalOf(result.error);
      if (refused) {
        setRefusal(refused);
        setConfirming(false);
      }
      return;
    }
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } finally {
      // A full load drops every bit of client state of the deleted account.
      window.location.assign(LOGIN_PATH);
    }
  };

  const isPlatformTeam = me.user.is_platform_admin || me.platform_admin_role != null;
  return (
    <Card title={t("closure.account.title")} className="border-danger/40" data-testid="delete-account">
      <div className="space-y-3 text-sm">
        <p className="text-ink-muted">{t("closure.account.description")}</p>
        <p className="text-ink-muted">{t(isPlatformTeam ? "closure.account.platformNote" : "closure.account.ownerNote")}</p>
        {/* Announced once the dialog closes: the deletion was refused, and why. */}
        <div role="status">
          {refusal ? (
            <Alert tone="warning">
              {refusal.names === null ? refusal.text : <UserSentence text={refusal.text} values={{ names: refusal.names }} />}
            </Alert>
          ) : null}
        </div>
        {isPlatformTeam ? null : (
          <Button variant="danger" size="sm" onClick={() => setConfirming(true)} aria-haspopup="dialog">
            {t("closure.account.action")}
          </Button>
        )}
      </div>
      <ConfirmDialog
        open={isConfirming}
        onClose={() => setConfirming(false)}
        onConfirm={onDelete}
        title={t("closure.account.dialogTitle")}
        description={t("closure.account.dialogDescription")}
        confirmLabel={t("closure.account.confirm")}
        pendingLabel={t("closure.account.deleting")}
        confirmationText={account}
        isPending={remove.isPending}
        error={remove.error}
      />
    </Card>
  );
}

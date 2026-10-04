"use client";

/**
 * The authenticator app: its state, setting it up (QR code, first code,
 * then the recovery codes once) and turning it off.
 */

import { useState } from "react";

import { api } from "@/api/client";
import { toApiError } from "@/api/errors";
import { unwrap } from "@/api/result";
import type { AccountSecurityView, TotpEnrollmentView } from "@/api/types";
import { AuthenticatorSetup } from "@/components/security/AuthenticatorSetup";
import { RecoveryCodesPanel } from "@/components/security/RecoveryCodesPanel";
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  Modal,
  useToast,
} from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { formatDate, formatDateTime } from "@/lib/format";
import { secondFactorProblem } from "@/lib/security/secondFactor";

export function AuthenticatorCard({
  security,
  account,
  onChanged,
}: {
  security: AccountSecurityView;
  account: string;
  onChanged: () => Promise<void>;
}) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const [enrollment, setEnrollment] = useState<TotpEnrollmentView | null>(null);
  const [isStarting, setStarting] = useState(false);
  const [isConfirming, setConfirming] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [codes, setCodes] = useState<string[] | null>(null);
  const [isRemoving, setRemoving] = useState(false);
  const [askRemove, setAskRemove] = useState(false);

  const status = security.totp_status ?? null;

  const start = async () => {
    setStarting(true);
    setProblem(null);
    try {
      setEnrollment(await unwrap(api.POST("/v1/me/mfa/totp")));
    } catch (error) {
      toast.error(toApiError(error));
    } finally {
      setStarting(false);
    }
  };

  const confirm = async (code: string) => {
    setConfirming(true);
    setProblem(null);
    try {
      const answer = await unwrap(
        api.POST("/v1/me/mfa/totp/confirm", { body: { code } }),
      );
      setEnrollment(null);
      setCodes(answer.recovery_codes);
      toast.success(t("security.app.turnedOn"));
      await onChanged();
    } catch (caught) {
      const error = toApiError(caught);
      const key = secondFactorProblem(error);
      if (key) {
        setProblem(t(key));
      } else {
        toast.error(error);
      }
    } finally {
      setConfirming(false);
    }
  };

  const remove = async () => {
    setRemoving(true);
    try {
      await unwrap(api.DELETE("/v1/me/mfa/totp"));
      setAskRemove(false);
      toast.success(t("security.app.removed"));
      await onChanged();
    } catch (error) {
      toast.error(toApiError(error));
    } finally {
      setRemoving(false);
    }
  };

  const details: string[] = [];
  if (status === "active" && security.totp_confirmed_at) {
    details.push(
      t("security.app.since", {
        date: formatDate(security.totp_confirmed_at, { locale }),
      }),
    );
  }
  if (status === "active" && security.totp_last_used_at) {
    details.push(
      t("security.app.lastUsed", {
        date: formatDateTime(security.totp_last_used_at, { locale }),
      }),
    );
  }

  return (
    <Card
      title={t("security.app.title")}
      description={t("security.app.description")}
      actions={
        status === "active" ? (
          <Badge tone="success">{t("security.app.on")}</Badge>
        ) : (
          <Badge tone={status === "pending" ? "warning" : "neutral"}>
            {status === "pending"
              ? t("security.app.pending")
              : t("security.app.off")}
          </Badge>
        )
      }
    >
      <div className="space-y-4">
        {details.length > 0 ? (
          <p className="text-sm text-ink-muted">{details.join(" · ")}</p>
        ) : null}
        {security.is_mfa_required ? (
          <p className="text-sm text-ink-muted">
            {t("security.app.adminRequired")}
          </p>
        ) : null}
        <div className="flex flex-wrap gap-2">
          {status === "active" ? (
            <Button variant="secondary" onClick={() => setAskRemove(true)}>
              {t("security.app.remove")}
            </Button>
          ) : (
            <Button isLoading={isStarting} onClick={() => void start()}>
              {status === "pending"
                ? t("security.app.finishSetup")
                : t("security.app.setUp")}
            </Button>
          )}
        </div>
      </div>

      <Modal
        open={enrollment !== null}
        onClose={() => setEnrollment(null)}
        title={t("mfa.setup.title")}
      >
        {enrollment ? (
          <AuthenticatorSetup
            enrollment={enrollment}
            onConfirm={(code) => void confirm(code)}
            isConfirming={isConfirming}
            error={problem ?? undefined}
          />
        ) : null}
      </Modal>

      <Modal
        open={codes !== null}
        onClose={() => setCodes(null)}
        title={t("mfa.recovery.title")}
      >
        {codes ? (
          <RecoveryCodesPanel
            codes={codes}
            account={account}
            onDone={() => setCodes(null)}
            doneLabel={t("common.done")}
          />
        ) : null}
      </Modal>

      <ConfirmDialog
        open={askRemove}
        onClose={() => setAskRemove(false)}
        onConfirm={remove}
        isPending={isRemoving}
        title={t("security.app.removeTitle")}
        confirmLabel={t("security.app.remove")}
      >
        <p>{t("security.app.removeDescription")}</p>
        {security.is_mfa_required ? (
          <p className="mt-2">{t("security.app.removeAdmin")}</p>
        ) : null}
      </ConfirmDialog>
    </Card>
  );
}

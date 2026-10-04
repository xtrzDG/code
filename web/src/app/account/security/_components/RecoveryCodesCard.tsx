"use client";

/** How many recovery codes are left, and a new set (the old one stops working). */

import { useState } from "react";

import { api } from "@/api/client";
import { toApiError } from "@/api/errors";
import { unwrap } from "@/api/result";
import { RecoveryCodesPanel } from "@/components/security/RecoveryCodesPanel";
import { Button, Card, ConfirmDialog, Modal, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

export function RecoveryCodesCard({
  left,
  account,
  onChanged,
}: {
  left: number;
  account: string;
  onChanged: () => Promise<void>;
}) {
  const { t, tp } = useI18n();
  const toast = useToast();
  const [asking, setAsking] = useState(false);
  const [isRenewing, setRenewing] = useState(false);
  const [codes, setCodes] = useState<string[] | null>(null);

  const renew = async () => {
    setRenewing(true);
    try {
      const answer = await unwrap(api.POST("/v1/me/mfa/recovery-codes"));
      setAsking(false);
      setCodes(answer.recovery_codes);
      await onChanged();
    } catch (error) {
      toast.error(toApiError(error));
    } finally {
      setRenewing(false);
    }
  };

  return (
    <Card
      title={t("security.codes.title")}
      description={t("security.codes.description")}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className={left > 0 ? "text-sm text-ink" : "text-sm text-warning"}>
          {left > 0
            ? tp("security.codes.left", left)
            : t("security.codes.none")}
        </p>
        <Button variant="secondary" onClick={() => setAsking(true)}>
          {t("security.codes.renew")}
        </Button>
      </div>

      <ConfirmDialog
        open={asking}
        onClose={() => setAsking(false)}
        onConfirm={renew}
        tone="primary"
        isPending={isRenewing}
        pendingLabel={t("security.codes.renewing")}
        title={t("security.codes.renewTitle")}
        confirmLabel={t("security.codes.renew")}
      >
        <p>{t("security.codes.renewDescription")}</p>
      </ConfirmDialog>

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
    </Card>
  );
}

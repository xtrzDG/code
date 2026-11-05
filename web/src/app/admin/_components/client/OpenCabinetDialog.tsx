"use client";

import { useState } from "react";

import { ConfirmDialog, Field, Textarea, UserSentence } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { SUPPORT_REASON_MAX, cleanSupportReason, isSupportReasonValid } from "../../_lib/supportReason";

/**
 * "Open cabinet" asks why: the owner sees the reason in their banner and
 * the audit log keeps it. The look lasts an hour and is read only.
 */
export function OpenCabinetDialog({
  open,
  name,
  isPending,
  error,
  onClose,
  onOpen,
}: {
  open: boolean;
  name: string;
  isPending: boolean;
  error: unknown;
  onClose: () => void;
  onOpen: (reason: string) => void | Promise<void>;
}) {
  const { t } = useI18n();
  const [reason, setReason] = useState("");
  const [isTouched, setTouched] = useState(false);
  // Each opening starts with an empty reason.
  const [wasOpen, setWasOpen] = useState(open);
  if (wasOpen !== open) {
    setWasOpen(open);
    if (open) {
      setReason("");
      setTouched(false);
    }
  }
  const isValid = isSupportReasonValid(reason);

  return (
    <ConfirmDialog
      open={open}
      onClose={onClose}
      onConfirm={() => onOpen(cleanSupportReason(reason))}
      tone="primary"
      isPending={isPending}
      pendingLabel={t("admin.detail.opening")}
      confirmDisabled={!isValid}
      error={error}
      title={<UserSentence text={t("admin.detail.openTitle")} values={{ name }} />}
      description={t("admin.detail.openDescription")}
      confirmLabel={t("admin.detail.openCabinet")}
    >
      <Field
        label={t("admin.detail.reasonLabel")}
        hint={t("admin.detail.reasonHint")}
        error={isTouched && !isValid ? t("admin.detail.reasonShort") : undefined}
        required
      >
        {(control) => (
          <Textarea
            {...control}
            value={reason}
            maxLength={SUPPORT_REASON_MAX}
            rows={3}
            onChange={(event) => setReason(event.target.value)}
            onBlur={() => setTouched(true)}
          />
        )}
      </Field>
    </ConfirmDialog>
  );
}

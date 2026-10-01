"use client";

import type { ReactNode } from "react";

import { Button, Modal, type ButtonVariant } from "@/components/ui";
import { useI18n } from "@/i18n/client";

/**
 * A confirmation for an action that cannot be undone or reaches customers
 * (delete, publish, roll back). Cancel is the default focus target.
 */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  pendingLabel,
  variant = "danger",
  isPending = false,
  confirmDisabled = false,
  onConfirm,
  onClose,
  children,
}: {
  open: boolean;
  title: ReactNode;
  description?: ReactNode;
  confirmLabel: string;
  pendingLabel?: string;
  variant?: ButtonVariant;
  isPending?: boolean;
  confirmDisabled?: boolean;
  onConfirm: () => void;
  onClose: () => void;
  children?: ReactNode;
}) {
  const { t } = useI18n();
  return (
    <Modal
      open={open}
      onClose={() => {
        if (!isPending) {
          onClose();
        }
      }}
      title={title}
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={isPending} autoFocus>
            {t("common.cancel")}
          </Button>
          <Button variant={variant} onClick={onConfirm} isLoading={isPending} loadingText={pendingLabel} disabled={confirmDisabled}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div className="space-y-4 text-sm text-ink-muted">
        {description ? <p>{description}</p> : null}
        {children}
      </div>
    </Modal>
  );
}

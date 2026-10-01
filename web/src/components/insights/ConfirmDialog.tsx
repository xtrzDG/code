"use client";

import type { ReactNode } from "react";

import { Button, Modal } from "@/components/ui";
import { useI18n } from "@/i18n/client";

/**
 * Asks before a destructive or irreversible action:
 *
 *     <ConfirmDialog open={...} title="Cancel this booking?" confirmLabel="Cancel the booking"
 *       tone="danger" isPending={cancel.isPending} onConfirm={...} onClose={...} />
 */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  cancelLabel,
  tone = "danger",
  isPending = false,
  onConfirm,
  onClose,
  children,
}: {
  open: boolean;
  title: ReactNode;
  description?: ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  tone?: "danger" | "primary";
  isPending?: boolean;
  onConfirm: () => void;
  onClose: () => void;
  children?: ReactNode;
}) {
  const { t } = useI18n();
  return (
    <Modal
      open={open}
      onClose={isPending ? () => undefined : onClose}
      title={title}
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={isPending}>
            {cancelLabel ?? t("common.cancel")}
          </Button>
          <Button variant={tone} onClick={onConfirm} isLoading={isPending}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      {description ? <p className="text-sm text-ink-muted">{description}</p> : null}
      {children}
    </Modal>
  );
}

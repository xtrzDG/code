"use client";

import { useState, type FormEvent, type ReactNode } from "react";

import type { ErrorMessageOverrides } from "@/api/errors";
import { useI18n } from "@/i18n/client";

import { Button } from "./Button";
import { isConfirmationTyped } from "./confirmation";
import { Input } from "./controls";
import { Field } from "./Field";
import { InlineError } from "./InlineError";
import { Modal } from "./Modal";

export interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  /** Runs the action; the dialog stays open (the button spins) while `isPending`. */
  onConfirm: () => void | Promise<void>;
  title: ReactNode;
  description?: ReactNode;
  confirmLabel: string;
  /** The confirm button's text while the action runs ("Publishing…"). */
  pendingLabel?: string;
  cancelLabel?: string;
  /** "danger" (red, the default) for destructive actions; "primary" otherwise. */
  tone?: "danger" | "primary";
  isPending?: boolean;
  /** Keeps the action disabled (a choice in the body is missing). */
  confirmDisabled?: boolean;
  /**
   * A strong confirmation: the person must type this text (a name, a
   * number, a word) before the action is enabled.
   */
  confirmationText?: string;
  /** The last failure of the action, shown in the dialog (toasts sit under it). */
  error?: unknown;
  errorOverrides?: ErrorMessageOverrides;
  children?: ReactNode;
}

/**
 * Asks before an action that cannot be undone or reaches customers: delete,
 * publish, cancel a booking, disconnect a channel. Cancel takes the focus
 * (the safe choice) unless a confirmation must be typed; Enter confirms.
 */
export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel,
  pendingLabel,
  cancelLabel,
  tone = "danger",
  isPending = false,
  confirmDisabled = false,
  confirmationText,
  error,
  errorOverrides,
  children,
}: ConfirmDialogProps) {
  const { t } = useI18n();
  const [typed, setTyped] = useState("");
  // Each opening starts with an empty confirmation (one dialog element, so it can fade out).
  const [wasOpen, setWasOpen] = useState(open);
  if (wasOpen !== open) {
    setWasOpen(open);
    if (open) {
      setTyped("");
    }
  }
  const isUnlocked = confirmationText === undefined || isConfirmationTyped(typed, confirmationText);
  const canConfirm = isUnlocked && !confirmDisabled && !isPending;

  const confirm = async () => {
    if (canConfirm) {
      await onConfirm();
    }
  };
  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void confirm();
  };

  return (
    <Modal
      open={open}
      onClose={isPending ? () => undefined : onClose}
      title={title}
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={isPending} autoFocus={confirmationText === undefined}>
            {cancelLabel ?? t("common.cancel")}
          </Button>
          <Button
            variant={tone}
            onClick={() => void confirm()}
            isLoading={isPending}
            loadingText={pendingLabel}
            disabled={!isUnlocked || confirmDisabled}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4 text-sm text-ink-muted" noValidate>
        {description ? <p>{description}</p> : null}
        {children}
        {confirmationText !== undefined ? (
          <Field label={t("common.typeToConfirm", { text: confirmationText })}>
            {(control) => (
              <Input
                {...control}
                value={typed}
                autoFocus
                autoComplete="off"
                autoCapitalize="off"
                spellCheck={false}
                dir="auto"
                onChange={(event) => setTyped(event.target.value)}
              />
            )}
          </Field>
        ) : null}
        <InlineError error={error} overrides={errorOverrides} />
      </form>
    </Modal>
  );
}

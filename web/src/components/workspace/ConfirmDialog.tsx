"use client";

import { useState, type FormEvent, type ReactNode } from "react";

import type { ErrorMessageOverrides } from "@/api/errors";
import { Button, Field, Input, Modal } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { isConfirmationTyped } from "./helpers";
import { InlineError } from "./InlineError";

export interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  /** Runs the action; the dialog stays open (with a spinner) until it settles. */
  onConfirm: () => void | Promise<void>;
  title: ReactNode;
  description?: ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  /** "danger" for destructive actions (red button). */
  tone?: "danger" | "primary";
  isPending?: boolean;
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
 * Asks before an action: "Disconnect Telegram?" with Cancel / Disconnect.
 * With `confirmationText` the action stays disabled until that text is typed.
 */
export function ConfirmDialog(props: ConfirmDialogProps) {
  // A new body per opening resets the typed confirmation.
  return <ConfirmDialogBody key={props.open ? "open" : "closed"} {...props} />;
}

function ConfirmDialogBody({
  open,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel,
  cancelLabel,
  tone = "danger",
  isPending = false,
  confirmationText,
  error,
  errorOverrides,
  children,
}: ConfirmDialogProps) {
  const { t } = useI18n();
  const [typed, setTyped] = useState("");
  const isUnlocked = confirmationText === undefined || isConfirmationTyped(typed, confirmationText);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isUnlocked && !isPending) {
      await onConfirm();
    }
  };

  return (
    <Modal open={open} onClose={isPending ? () => undefined : onClose} title={title} description={description} size="sm">
      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        {children ? <div className="space-y-3 text-sm text-ink-muted">{children}</div> : null}
        {confirmationText !== undefined ? (
          <Field label={t("workspace.typeToConfirm", { text: confirmationText })}>
            {(control) => (
              <Input
                {...control}
                value={typed}
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
        <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button variant="secondary" onClick={onClose} disabled={isPending}>
            {cancelLabel ?? t("common.cancel")}
          </Button>
          <Button type="submit" variant={tone === "danger" ? "danger" : "primary"} isLoading={isPending} disabled={!isUnlocked}>
            {confirmLabel}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

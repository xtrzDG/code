"use client";

import { useState, type ReactNode } from "react";

import type { Schema } from "@/api/types";
import type { ApiResult } from "@/api/result";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { Alert, ConfirmDialog, Field, Textarea, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { ADMIN_REASON_MAX, cleanReason, isReasonValid } from "../../../_lib/accountActions";

/** What every account action dialog is given by the menu. */
export interface AccountActionDialogProps {
  businessId: string;
  name: string;
  open: boolean;
  onClose: () => void;
}

/**
 * An account action sent with its reason: on success a toast, the client's
 * page (account, invoices, timeline) loads again and the dialog closes; a
 * refusal stays in the dialog. A step-up the API asks for is handled by
 * the API client before the action is retried.
 */
export function useAccountAction<Body>(
  businessId: string,
  call: (body: Body) => Promise<ApiResult<Schema<"AdminActionReceipt">>>,
  onDone: () => void,
) {
  const { t } = useI18n();
  const toast = useToast();
  const mutation = useMutation(call, { errorToast: false, invalidate: [queryKeys.admin.client(businessId)] });
  const submit = async (body: Body) => {
    const result = await mutation.run(body);
    if (result.ok) {
      toast.success(t("adminActions.done"));
      onDone();
    }
  };
  return { submit, isPending: mutation.isPending, error: mutation.error };
}

/**
 * The frame of an account action: what it does, its own fields, the reason
 * the audit log keeps (8 to 300 characters) and, where it matters, a note.
 * A fresh dialog (the menu remounts it) starts with an empty reason.
 */
export function ActionDialog({
  open,
  title,
  description,
  confirmLabel,
  tone = "primary",
  fieldsValid = true,
  isPending,
  error,
  note,
  onClose,
  onConfirm,
  children,
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  tone?: "primary" | "danger";
  fieldsValid?: boolean;
  isPending: boolean;
  error: unknown;
  note?: ReactNode;
  onClose: () => void;
  onConfirm: (reason: string) => void | Promise<void>;
  children?: ReactNode;
}) {
  const { t } = useI18n();
  const [reason, setReason] = useState("");
  const [isTouched, setTouched] = useState(false);
  const isValid = isReasonValid(reason);

  return (
    <ConfirmDialog
      open={open}
      onClose={onClose}
      onConfirm={() => onConfirm(cleanReason(reason))}
      tone={tone}
      isPending={isPending}
      confirmDisabled={!isValid || !fieldsValid}
      error={error}
      title={title}
      description={description}
      confirmLabel={confirmLabel}
    >
      <div className="space-y-4">
        {children}
        <Field
          label={t("adminActions.reasonLabel")}
          hint={t("adminActions.reasonHint")}
          error={isTouched && !isValid ? t("adminActions.reasonShort") : undefined}
          required
        >
          {(control) => (
            <Textarea
              {...control}
              value={reason}
              maxLength={ADMIN_REASON_MAX}
              rows={3}
              onChange={(event) => setReason(event.target.value)}
              onBlur={() => setTouched(true)}
            />
          )}
        </Field>
        {note ? <Alert tone="info">{note}</Alert> : null}
      </div>
    </ConfirmDialog>
  );
}

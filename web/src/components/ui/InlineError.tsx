"use client";

import { describeError, type ErrorMessageOverrides } from "@/api/errors";
import { Alert } from "./Alert";
import { useI18n } from "@/i18n/client";

/**
 * A failed action shown inside a dialog or form. Toasts sit under an open
 * modal dialog (the dialog is in the top layer), so dialogs show errors here.
 */
export function InlineError({
  error,
  overrides,
  className,
}: {
  error: unknown;
  overrides?: ErrorMessageOverrides;
  className?: string;
}) {
  const { t } = useI18n();
  if (!error) {
    return null;
  }
  const { title, detail, requestId } = describeError(error, t, overrides);
  const lines = [detail, requestId ? t("common.requestId", { id: requestId }) : null].filter(Boolean);
  return (
    <Alert tone="danger" title={title} className={className}>
      {lines.length > 0 ? lines.join(" · ") : null}
    </Alert>
  );
}

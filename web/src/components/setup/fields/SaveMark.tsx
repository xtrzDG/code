"use client";

/**
 * Whether one line of a list is saved: a spinner while it is, a tick once
 * it is, a warning when it could not be (the reason is under the line).
 * An empty slot of the same size before the first save, so lines align.
 */

import { IconAlert, IconCheck } from "@/components/icons";
import { Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";

export type LineSaveStatus = "saving" | "saved" | "failed";

export function SaveMark({ status }: { status: LineSaveStatus | undefined }) {
  const { t } = useI18n();
  if (!status) {
    return <span className="size-4 shrink-0" aria-hidden />;
  }
  const label = status === "saving" ? t("tunnelOffer.offer.rowSaving") : status === "saved" ? t("tunnelOffer.offer.rowSaved") : t("tunnelOffer.offer.rowFailed");
  return (
    <span title={label} className="flex size-4 shrink-0 items-center justify-center self-center">
      {status === "saving" ? (
        <Spinner size="sm" />
      ) : status === "saved" ? (
        <IconCheck className="size-4 text-success" aria-hidden />
      ) : (
        <IconAlert className="size-4 text-warning" aria-hidden />
      )}
      <span className="sr-only">{label}</span>
    </span>
  );
}

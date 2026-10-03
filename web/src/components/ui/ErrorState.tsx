"use client";

import { describeError } from "@/api/errors";
import { useI18n } from "@/i18n/client";

import { IconAlert } from "../icons";
import { Button } from "./Button";
import { EmptyState } from "./EmptyState";

/** A failed load with a localized reason and a retry button. */
export function ErrorState({
  error,
  onRetry,
  className,
}: {
  error: unknown;
  onRetry?: () => void;
  className?: string;
}) {
  const { t } = useI18n();
  const { title, detail, requestId } = describeError(error, t);
  return (
    <EmptyState
      className={className}
      icon={<IconAlert className="size-6" />}
      title={title}
      description={[detail, requestId ? t("common.requestId", { id: requestId }) : null]
        .filter(Boolean)
        .join(" · ")}
      action={
        onRetry ? (
          <Button variant="secondary" onClick={onRetry}>
            {t("common.retry")}
          </Button>
        ) : undefined
      }
    />
  );
}

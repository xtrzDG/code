"use client";

/**
 * Why the last save of a part of the profile did not go through, under
 * that part ("This is not a phone number"), until a later save does.
 */

import { describeError, type ApiError } from "@/api/errors";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

export function SaveProblem({ error, className }: { error: ApiError | null; className?: string }) {
  const { t } = useI18n();
  if (!error) {
    return null;
  }
  const { title, detail } = describeError(error, t);
  return (
    <p role="alert" className={cn("text-sm text-danger", className)}>
      {title}
      {detail ? <span className="block text-ink-muted">{detail}</span> : null}
    </p>
  );
}

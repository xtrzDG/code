"use client";

/**
 * The line over a form that saves itself: there is no Save button, changes
 * are saved as they are made, and here is the state of the latest ones
 * ("Saving…", "Saved", "Not saved"), like the profile editor's.
 */

import { IconAlert, IconCheck } from "@/components/icons";
import { Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import type { SaveState } from "./saveTracking";

export function AutosaveHint({ state, className }: { state: SaveState; className?: string }) {
  const { t } = useI18n();
  return (
    <p
      role="status"
      data-autosave-state={state}
      className={cn(
        "inline-flex min-h-7 items-center gap-1.5 rounded-full px-3 text-xs font-medium",
        state === "failed" ? "bg-warning-soft text-warning" : "bg-surface-muted/80 text-ink-muted",
        className,
      )}
    >
      {state === "saving" ? (
        <Spinner size="sm" />
      ) : state === "failed" ? (
        <IconAlert className="size-3.5" aria-hidden />
      ) : (
        <IconCheck className={cn("size-3.5", state === "saved" && "text-success")} aria-hidden />
      )}
      {t(
        state === "saving"
          ? "formFields.autosave.saving"
          : state === "saved"
            ? "formFields.autosave.saved"
            : state === "failed"
              ? "formFields.autosave.failed"
              : "formFields.autosave.hint",
      )}
    </p>
  );
}

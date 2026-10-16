"use client";

/**
 * Whether one field's last change is saved, beside its label: "Saving…"
 * while it is, "Saved" for a few seconds after, "Not saved · Try again"
 * when it failed (a lost connection is retried by itself meanwhile).
 * Read out politely by screen readers; an empty slot of the same height
 * otherwise, so nothing moves.
 */

import { useEffect, useState } from "react";

import { IconAlert, IconCheck } from "@/components/icons";
import { Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import type { FieldSaveState } from "./autosaveTypes";

/** How long "Saved" stays after a save. */
const SAVED_VISIBLE_MS = 6_000;

export function SavePill({ state, onRetry, className }: { state: FieldSaveState; onRetry?: () => void; className?: string }) {
  const { t } = useI18n();
  const savedAt = state.status === "saved" ? state.savedAt : null;
  // The save whose "Saved" has been shown long enough.
  const [expired, setExpired] = useState<number | null>(null);
  const isFresh = savedAt !== null && expired !== savedAt;

  useEffect(() => {
    if (savedAt === null) {
      return;
    }
    const timer = setTimeout(() => setExpired(savedAt), Math.max(0, SAVED_VISIBLE_MS - (Date.now() - savedAt)));
    return () => clearTimeout(timer);
  }, [savedAt]);

  const shown = state.status === "saving" ? "saving" : state.status === "failed" ? "failed" : isFresh ? "saved" : null;
  return (
    <span className={cn("inline-flex min-h-5 items-center gap-2", className)}>
      <span role="status" className="inline-flex">
        {shown ? (
          <span
            data-save-status={shown}
            className={cn(
              "animate-settle inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap",
              shown === "failed" ? "bg-warning-soft text-warning" : "bg-surface-muted text-ink-muted",
            )}
          >
            {shown === "saving" ? (
              <Spinner size="sm" />
            ) : shown === "saved" ? (
              <IconCheck className="size-3.5 text-success" aria-hidden />
            ) : (
              <IconAlert className="size-3.5" aria-hidden />
            )}
            {t(shown === "saving" ? "formFields.autosave.saving" : shown === "saved" ? "formFields.autosave.saved" : "formFields.autosave.failed")}
          </span>
        ) : null}
      </span>
      {shown === "failed" && onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="rounded text-xs font-medium text-accent underline underline-offset-2 hover:no-underline focus-visible:outline-2 focus-visible:outline-focus"
        >
          {t("formFields.autosave.retry")}
        </button>
      ) : null}
    </span>
  );
}

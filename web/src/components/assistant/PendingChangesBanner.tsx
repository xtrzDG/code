"use client";

/**
 * The strip over every page of the cabinet while customers do not get
 * the owner's changes yet: "2 changes are not with your customers yet ·
 * Review and apply" (the sheet with the list), "Applying your changes…"
 * while they go live, or why they stopped. Hidden when nothing is
 * pending, and for staff.
 */

import { IconAlert, IconSparkles } from "@/components/icons";
import { Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { useApplyChanges } from "./ApplyChangesContext";

export function PendingChangesBanner() {
  const { t, tp } = useI18n();
  const { canApply, pending, apply, open } = useApplyChanges();
  const count = pending.data?.is_live ? pending.data.count : 0;
  const view = apply.view;

  if (!canApply) {
    return null;
  }
  const isRunning = apply.phase === "running";
  const isStopped = !isRunning && apply.phase === "attention";
  if (!isRunning && count === 0) {
    return null;
  }

  const total = view?.checks_total ?? 0;
  const text = isRunning
    ? view?.stage === "checking" && total > 0
      ? t("applyChanges.banner.checking", { done: view.checks_done ?? 0, total })
      : t("applyChanges.banner.running")
    : isStopped
      ? t("applyChanges.banner.attention")
      : tp("applyChanges.banner.pending", count);
  const action = isRunning
    ? t("applyChanges.banner.watch")
    : isStopped
      ? t("applyChanges.banner.seeWhy")
      : t("applyChanges.banner.review");

  return (
    <div
      role="status"
      data-testid="pending-changes-banner"
      className={cn(
        "mb-5 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-2xl border px-4 py-3 text-sm",
        isStopped ? "border-warning/40 bg-warning-soft/60" : "border-accent/30 bg-accent-soft/60",
      )}
    >
      <span className={cn("flex shrink-0", isStopped ? "text-warning" : "text-accent")} aria-hidden>
        {isRunning ? <Spinner size="sm" /> : isStopped ? <IconAlert className="size-5" /> : <IconSparkles className="size-5" />}
      </span>
      <span className="min-w-0 font-medium text-ink">{text}</span>
      <span className="hidden text-ink-subtle sm:inline" aria-hidden>
        ·
      </span>
      <button
        type="button"
        onClick={open}
        aria-haspopup="dialog"
        className="inline-flex min-h-9 cursor-pointer items-center rounded-lg px-2 font-medium text-accent underline-offset-4 transition-colors hover:bg-surface/70 hover:underline focus-visible:outline-2 focus-visible:outline-focus pointer-coarse:min-h-11"
      >
        {action}
      </button>
    </div>
  );
}

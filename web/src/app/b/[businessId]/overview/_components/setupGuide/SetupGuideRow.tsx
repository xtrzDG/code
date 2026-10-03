"use client";

/**
 * One step of the setup guide: its state (done, skipped, next, to do),
 * what it is for and how long it takes, the button that leads there, and
 * "Skip" for an optional step. The phone check opens in place.
 */

import type { ReactNode } from "react";

import { IconArrowRight, IconCheck } from "@/components/icons";
import { Badge, Button, ButtonLink } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import type { GuideRow } from "@/lib/setupGuide/guide";

function StateMark({ status }: { status: GuideRow["step"]["status"] }) {
  if (status === "done") {
    return (
      <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-success-soft text-success">
        <IconCheck className="size-3.5" aria-hidden />
      </span>
    );
  }
  return (
    <span
      aria-hidden
      className={cn(
        "size-6 shrink-0 rounded-full border-2",
        status === "next" ? "border-accent-solid bg-accent-soft" : "border-line",
        status === "skipped" && "border-dashed",
      )}
    />
  );
}

export function SetupGuideRow({
  row,
  isOpen,
  onToggle,
  onSkip,
  isBusy,
  children,
}: {
  row: GuideRow;
  /** The phone check is shown under the row. */
  isOpen: boolean;
  onToggle: () => void;
  onSkip: (isSkipped: boolean) => void;
  isBusy: boolean;
  /** What opens under the row (the phone check). */
  children?: ReactNode;
}) {
  const { t } = useI18n();
  const { step } = row;
  const isNext = step.status === "next";
  const isDone = step.status === "done";
  const variant = isNext ? "primary" : "secondary";

  return (
    <li className="py-3 first:pt-0 last:pb-0">
      <div className="flex gap-3">
        <StateMark status={step.status} />
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className={cn("text-sm font-semibold", isDone || step.status === "skipped" ? "text-ink-muted" : "text-ink")}>
              {step.title}
            </h3>
            {isNext ? <Badge tone="accent">{t("setupGuide.status.next")}</Badge> : null}
            {step.status === "skipped" ? <Badge tone="neutral">{t("setupGuide.status.skipped")}</Badge> : null}
          </div>
          {isDone ? null : <p className="text-sm text-ink-muted">{step.description}</p>}
          {isDone || step.status === "skipped" ? null : (
            <p className="text-xs text-ink-subtle">
              {t("setupGuide.minutes", { count: step.minutes })}
              {step.is_required ? "" : ` · ${t("setupGuide.optional")}`}
            </p>
          )}
        </div>
        {isDone ? null : (
          <div className="flex shrink-0 flex-col items-end gap-1 sm:flex-row sm:items-center">
            {step.status === "skipped" ? null : row.kind === "phone" ? (
              <Button size="sm" variant={variant} onClick={onToggle} aria-expanded={isOpen}>
                {isOpen ? t("setupGuide.phone.hide") : step.action.label}
              </Button>
            ) : row.href ? (
              <ButtonLink
                size="sm"
                variant={variant}
                href={row.href}
                trailingIcon={<IconArrowRight className="size-4" aria-hidden />}
              >
                {step.action.label}
              </ButtonLink>
            ) : null}
            {row.canSkip ? (
              <Button
                size="sm"
                variant="ghost"
                disabled={isBusy}
                onClick={() => onSkip(step.status !== "skipped")}
                aria-label={t(step.status === "skipped" ? "setupGuide.unskipLabel" : "setupGuide.skipLabel", {
                  step: step.title,
                })}
              >
                {t(step.status === "skipped" ? "setupGuide.unskip" : "setupGuide.skip")}
              </Button>
            ) : null}
          </div>
        )}
      </div>
      {isOpen && children ? <div className="mt-3 sm:ps-9">{children}</div> : null}
    </li>
  );
}

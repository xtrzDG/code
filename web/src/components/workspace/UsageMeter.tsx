"use client";

import { useId, type ReactNode } from "react";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";

import { usageLevel, type UsageLevel } from "@/lib/usage";

import { usageBarWidth } from "./helpers";

const BAR_COLORS: Record<UsageLevel, string> = {
  none: "bg-line-strong",
  ok: "bg-accent-solid",
  warning: "bg-warning",
  exceeded: "bg-danger-solid",
};

/**
 * Package usage: "Voice minutes — 320 of 400 (80 %)" with a bar that turns
 * amber from 80 % and red at 100 %.
 */
export function UsageMeter({
  label,
  usedText,
  percent,
  hint,
  className,
}: {
  label: ReactNode;
  /** "320 of 400 min" (already formatted). */
  usedText: ReactNode;
  /** Whole percent, or null when the package has none of this unit. */
  percent: number | null | undefined;
  hint?: ReactNode;
  className?: string;
}) {
  const { t, locale } = useI18n();
  const labelId = useId();
  const level = usageLevel(percent);
  const width = usageBarWidth(percent);
  const percentText =
    percent === null || percent === undefined
      ? t("workspace.usage.notIncluded")
      : formatNumber(percent / 100, locale, { style: "percent", maximumFractionDigits: 0 });

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <span id={labelId} className="text-sm font-medium text-ink">
          {label}
        </span>
        <span className="text-sm text-ink-muted">
          {usedText}
          <span
            className={cn(
              "ml-2 font-medium",
              level === "warning" && "text-warning",
              level === "exceeded" && "text-danger",
              (level === "ok" || level === "none") && "text-ink",
            )}
          >
            {percentText}
          </span>
        </span>
      </div>
      <div
        role="meter"
        aria-labelledby={labelId}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent ?? 0}
        aria-valuetext={percentText}
        className="h-2.5 w-full overflow-hidden rounded-full bg-surface-muted ring-1 ring-line ring-inset"
      >
        <div className={cn("h-full rounded-full transition-[width]", BAR_COLORS[level])} style={{ width: `${width}%` }} />
      </div>
      {hint ? <p className="text-xs text-ink-subtle">{hint}</p> : null}
    </div>
  );
}

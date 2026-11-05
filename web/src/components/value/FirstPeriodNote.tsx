"use client";

import { IconInfo } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

/**
 * Said once per card when the period before had no activity at all: no
 * change chip on any number then (each would present its whole total as
 * growth), only "First period: nothing to compare with yet".
 */
export function FirstPeriodNote({ className }: { className?: string }) {
  const { t } = useI18n();
  return (
    <p data-first-period="" className={cn("flex items-center gap-1.5 text-xs text-ink-muted", className)}>
      <IconInfo className="size-3.5 shrink-0" aria-hidden />
      <span>{t("value.delta.firstPeriodNote")}</span>
    </p>
  );
}

"use client";

import { useId } from "react";

import { IconClock, IconRefresh } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";

import { DeltaChip } from "./DeltaChip";
import { growthLines, type GrowthOrigin } from "./growthLines";
import { formatWholeMoney, type ValueTotals } from "./valueModel";

const ICONS: Record<GrowthOrigin, typeof IconClock> = { waitlist: IconClock, campaign: IconRefresh };
const COUNT_KEYS = { waitlist: "growthValue.waitlist", campaign: "growthValue.campaign" } as const;
const HINT_KEYS = { waitlist: "growthValue.waitlistHint", campaign: "growthValue.campaignHint" } as const;

/**
 * The bookings the waitlist filled and those the return-visit messages
 * brought back, each on its own line with its worth and change (nothing
 * when the period and the one before had none).
 */
export function GrowthLines({
  current,
  previous,
  currency,
  days,
  isFirstPeriod,
  className,
}: {
  current: ValueTotals;
  previous: ValueTotals;
  currency: string;
  days: number;
  isFirstPeriod: boolean;
  className?: string;
}) {
  const { t, tp, locale } = useI18n();
  const titleId = useId();
  const lines = growthLines(current, previous);
  if (lines.length === 0) {
    return null;
  }
  return (
    <section aria-labelledby={titleId} className={cn("space-y-2", className)}>
      <h3 id={titleId} className="text-xs font-semibold tracking-wide text-ink-muted uppercase">
        {t("growthValue.label")}
      </h3>
      <ul className="grid gap-2 sm:grid-cols-2">
        {lines.map((line) => {
          const Icon = ICONS[line.origin];
          return (
            <li key={line.origin} className="flex items-start gap-3 rounded-2xl border border-line bg-surface/80 p-3">
              <span aria-hidden className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent">
                <Icon className="size-4" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <span className="text-sm font-semibold text-ink tabular-nums">
                    {tp(COUNT_KEYS[line.origin], line.count, { count: formatNumber(line.count, locale) })}
                  </span>
                  {line.valueMinor !== null ? (
                    <span className="text-sm font-semibold text-accent tabular-nums">
                      {t("growthValue.worth", { money: formatWholeMoney(line.valueMinor, currency, locale) })}
                    </span>
                  ) : null}
                  <DeltaChip current={line.count} previous={line.previousCount} days={days} isFirstPeriod={isFirstPeriod} />
                </span>
                <span className="mt-0.5 block text-xs text-ink-muted">{t(HINT_KEYS[line.origin])}</span>
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

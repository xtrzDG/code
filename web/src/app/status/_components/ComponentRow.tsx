"use client";

import { Badge } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatDate, formatNumber } from "@/lib/format";
import { DAY_COLOURS, LEVEL_TONES, historySummary, type HistorySummary, type PlatformStatus } from "@/lib/help/platformStatus";

type ComponentStatus = PlatformStatus["components"][number];

/**
 * One part of the platform: how it is now and its last 90 days as bars,
 * oldest on the start side (each bar names its day and level when pointed
 * at), with the share of days without trouble once a week is measured, and
 * since when it is observed before that.
 */
export function ComponentRow({ component }: { component: ComponentStatus }) {
  const { t, tp, locale } = useI18n();
  const name = t(`platformStatus.components.${component.component}`);
  const summary = summaryText(historySummary(component.history), {
    none: () => t("platformStatus.noHistory"),
    // History days are calendar days ("2026-10-05"): written as such, in no time zone.
    observing: (since) =>
      t("platformStatus.observingSince", {
        date: formatDate(new Date(`${since}T12:00:00Z`), { locale, timeZone: "UTC", dateStyle: "long" }),
      }),
    share: (share, days) =>
      tp("platformStatus.uptime", days, { share: formatNumber(share, locale, { style: "percent", maximumFractionDigits: 1 }) }),
  });

  return (
    <li data-component={component.component} className="space-y-3 px-5 py-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-medium text-ink">{name}</h3>
          <p className="text-xs text-ink-muted">{summary}</p>
        </div>
        <Badge tone={LEVEL_TONES[component.level]} className="shrink-0">
          {t(`platformStatus.levels.${component.level}`)}
        </Badge>
      </div>
      <div role="img" aria-label={`${t("platformStatus.historyLabel", { component: name })}. ${summary}`} className="flex h-8 items-stretch gap-px" dir="ltr">
        {component.history.map((day) => (
          <span
            key={day.day}
            title={t("platformStatus.day", { day: day.day, level: t(`platformStatus.levels.${day.level}`) })}
            className={cn("min-w-0 flex-1 rounded-[2px]", DAY_COLOURS[day.level], day.level === "no_data" && "opacity-40")}
          />
        ))}
      </div>
      <div className="flex items-center justify-between gap-3 text-xs text-ink-subtle" aria-hidden>
        <span>{t("platformStatus.historyStart")}</span>
        <span>{t("platformStatus.historyEnd")}</span>
      </div>
    </li>
  );
}

function summaryText(
  summary: HistorySummary,
  texts: { none: () => string; observing: (since: string) => string; share: (share: number, days: number) => string },
): string {
  switch (summary.kind) {
    case "none":
      return texts.none();
    case "observing":
      return texts.observing(summary.since);
    case "share":
      return texts.share(summary.share, summary.days);
  }
}

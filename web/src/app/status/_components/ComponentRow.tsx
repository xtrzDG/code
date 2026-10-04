"use client";

import { Badge } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";
import { DAY_COLOURS, LEVEL_TONES, goodDayShare, type PlatformStatus } from "@/lib/help/platformStatus";

type ComponentStatus = PlatformStatus["components"][number];

/**
 * One part of the platform: how it is now and its last 90 days as bars,
 * oldest on the start side (each bar names its day and level when pointed
 * at), with the share of days without trouble.
 */
export function ComponentRow({ component }: { component: ComponentStatus }) {
  const { t, locale } = useI18n();
  const name = t(`platformStatus.components.${component.component}`);
  const share = goodDayShare(component.history);
  const summary =
    share === null
      ? t("platformStatus.noHistory")
      : t("platformStatus.uptime", { share: formatNumber(share, locale, { style: "percent", maximumFractionDigits: 1 }) });

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

"use client";

import { useId, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { formatLocalDate } from "@/components/insights/dates";
import type { DashboardDay } from "@/components/insights/types";
import { Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { cn } from "@/lib/cn";

import { nearestDayIndex, TREND_SERIES, trendAxis, trendPath, type TrendSeries } from "./dashboardModel";

/** Plot coordinates of the SVG (it stretches to the card; strokes do not scale). */
const WIDTH = 600;
const HEIGHT = 160;

/**
 * The chart tokens 1–3 of globals.css (blue, orange, green), stepped for
 * each theme and at least 3:1 on the card. Identity never rests on color
 * alone: the legend names each line and the table view lists every value.
 */
const SERIES_STYLE: Record<TrendSeries, { label: MessageKey; color: string }> = {
  conversation_count: { label: "dashboard.trend.requests", color: "text-chart-1" },
  booking_count: { label: "dashboard.trend.bookings", color: "text-chart-2" },
  handoff_count: { label: "dashboard.trend.handoffs", color: "text-chart-3" },
};

/**
 * Requests, bookings and handoffs per local day of the dashboard period:
 * three thin lines on one count axis, a crosshair with every value of the
 * hovered (or arrow-key focused) day, and the same numbers as a table.
 */
export function TrendChart({ days }: { days: readonly DashboardDay[] }) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const id = useId();
  const plotRef = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState<number | null>(null);

  const max = Math.max(0, ...days.flatMap((day) => TREND_SERIES.map((series) => day[series])));
  const axis = trendAxis(max);
  const totals = Object.fromEntries(
    TREND_SERIES.map((series) => [series, days.reduce((sum, day) => sum + day[series], 0)]),
  ) as Record<TrendSeries, number>;
  const shortDate = (date: string) => formatLocalDate(date, locale, { day: "numeric", month: "short" });
  const activeDay = active === null ? null : (days[active] ?? null);
  const activeLeft = active === null || days.length < 2 ? 0 : (active / (days.length - 1)) * 100;

  const readout = (day: DashboardDay) =>
    t("dashboard.trend.readout", {
      date: formatLocalDate(day.date, locale, { dateStyle: "full" }),
      requests: format.number(day.conversation_count),
      bookings: format.number(day.booking_count),
      handoffs: format.number(day.handoff_count),
    });

  const onPointer = (event: PointerEvent<HTMLDivElement>) => {
    const box = plotRef.current?.getBoundingClientRect();
    if (!box || box.width === 0) {
      return;
    }
    setActive(nearestDayIndex((event.clientX - box.left) / box.width, days.length));
  };

  const onKey = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
      event.preventDefault();
      const step = event.key === "ArrowRight" ? 1 : -1;
      setActive((current) => Math.min(days.length - 1, Math.max(0, (current ?? (step > 0 ? -1 : days.length)) + step)));
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      setActive(event.key === "Home" ? 0 : days.length - 1);
    } else if (event.key === "Escape") {
      setActive(null);
    }
  };

  return (
    <Card title={t("dashboard.trend.title")} description={t("dashboard.trend.description")}>
      <ul className="mb-4 flex flex-wrap gap-x-5 gap-y-2 text-sm" aria-label={t("dashboard.trend.legend")}>
        {TREND_SERIES.map((series) => (
          <li key={series} className="flex items-center gap-2">
            <span className={cn("h-0.5 w-4 rounded-full bg-current", SERIES_STYLE[series].color)} aria-hidden />
            <span className="text-ink-muted">{t(SERIES_STYLE[series].label)}</span>
            <span className="font-medium text-ink tabular-nums">{format.number(totals[series])}</span>
          </li>
        ))}
      </ul>

      {/* The graphic reads left to right in every language (time runs to the right, as the
          plot's positions and its arrow keys do); the texts inside keep their own direction. */}
      <div className="flex gap-2" dir="ltr">
        <div className="relative h-40 w-8 shrink-0 text-end text-xs text-ink-subtle tabular-nums" aria-hidden>
          {axis.ticks.map((tick) => (
            <span
              key={tick}
              className="absolute end-0 -translate-y-1/2"
              style={{ top: `${100 - (tick / axis.max) * 100}%` }}
            >
              {format.number(tick)}
            </span>
          ))}
        </div>
        <div className="min-w-0 flex-1">
          <div
            ref={plotRef}
            role="slider"
            tabIndex={0}
            aria-label={t("dashboard.trend.chartLabel", {
              from: shortDate(days[0]?.date ?? ""),
              to: shortDate(days.at(-1)?.date ?? ""),
            })}
            aria-valuemin={0}
            aria-valuemax={Math.max(0, days.length - 1)}
            aria-valuenow={active ?? 0}
            aria-valuetext={activeDay ? readout(activeDay) : t("dashboard.trend.keyboardHint")}
            aria-describedby={`${id}-hint`}
            onPointerMove={onPointer}
            onPointerDown={onPointer}
            onPointerLeave={() => setActive(null)}
            onKeyDown={onKey}
            onBlur={() => setActive(null)}
            className="relative h-40 touch-pan-y rounded-md focus-visible:outline-2 focus-visible:outline-offset-4"
          >
            <svg
              viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
              preserveAspectRatio="none"
              className="absolute inset-0 size-full overflow-visible"
              aria-hidden
            >
              {axis.ticks.map((tick) => (
                <line
                  key={tick}
                  x1={0}
                  x2={WIDTH}
                  y1={HEIGHT - (tick / axis.max) * HEIGHT}
                  y2={HEIGHT - (tick / axis.max) * HEIGHT}
                  className="stroke-line"
                  strokeWidth={1}
                  vectorEffect="non-scaling-stroke"
                />
              ))}
              {TREND_SERIES.map((series) => (
                <path
                  key={series}
                  d={trendPath(
                    days.map((day) => day[series]),
                    axis.max,
                    WIDTH,
                    HEIGHT,
                  )}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  strokeLinejoin="round"
                  strokeLinecap="round"
                  vectorEffect="non-scaling-stroke"
                  className={SERIES_STYLE[series].color}
                />
              ))}
            </svg>

            {activeDay ? (
              <>
                <span className="pointer-events-none absolute inset-y-0 w-px bg-line-strong" style={{ left: `${activeLeft}%` }} aria-hidden />
                {TREND_SERIES.map((series) => (
                  <span
                    key={series}
                    aria-hidden
                    className={cn(
                      "pointer-events-none absolute size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-current ring-2 ring-surface",
                      SERIES_STYLE[series].color,
                    )}
                    style={{ left: `${activeLeft}%`, top: `${100 - (activeDay[series] / axis.max) * 100}%` }}
                  />
                ))}
                <div
                  className={cn(
                    "pointer-events-none absolute top-0 z-10 min-w-36 rounded-lg border border-line bg-surface px-3 py-2 text-xs shadow-md",
                    activeLeft > 50 ? "-translate-x-[calc(100%+0.75rem)]" : "translate-x-3",
                  )}
                  style={{ left: `${activeLeft}%` }}
                  dir="auto"
                  aria-hidden
                >
                  <p className="mb-1 font-medium text-ink-muted">
                    {formatLocalDate(activeDay.date, locale, { weekday: "short", day: "numeric", month: "short" })}
                  </p>
                  <ul className="space-y-0.5">
                    {TREND_SERIES.map((series) => (
                      <li key={series} className="flex items-center gap-2">
                        <span className={cn("h-0.5 w-3 rounded-full bg-current", SERIES_STYLE[series].color)} />
                        <span className="font-semibold text-ink tabular-nums">{format.number(activeDay[series])}</span>
                        <span className="text-ink-muted">{t(SERIES_STYLE[series].label)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            ) : null}
          </div>
          <div className="mt-1.5 flex justify-between text-xs text-ink-subtle" aria-hidden>
            <span>{shortDate(days[0]?.date ?? "")}</span>
            {days.length > 2 ? <span>{shortDate(days[Math.floor((days.length - 1) / 2)]?.date ?? "")}</span> : null}
            <span>{shortDate(days.at(-1)?.date ?? "")}</span>
          </div>
          <p id={`${id}-hint`} className="sr-only">
            {t("dashboard.trend.keyboardHint")}
          </p>
        </div>
      </div>

      <details className="group mt-4 text-sm">
        <summary className="cursor-pointer text-accent hover:underline">{t("dashboard.trend.showTable")}</summary>
        <div className="mt-2 max-h-72 overflow-auto rounded-lg border border-line">
          <table className="w-full text-start text-sm">
            <caption className="sr-only">{t("dashboard.trend.title")}</caption>
            <thead className="sticky top-0 bg-surface-muted text-xs text-ink-muted">
              <tr>
                <th scope="col" className="px-3 py-2 font-medium">
                  {t("dashboard.trend.date")}
                </th>
                {TREND_SERIES.map((series) => (
                  <th key={series} scope="col" className="px-3 py-2 text-end font-medium">
                    {t(SERIES_STYLE[series].label)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {[...days].reverse().map((day) => (
                <tr key={day.date}>
                  <th scope="row" className="px-3 py-1.5 font-normal whitespace-nowrap text-ink">
                    {formatLocalDate(day.date, locale, { weekday: "short", day: "numeric", month: "short" })}
                  </th>
                  {TREND_SERIES.map((series) => (
                    <td key={series} className="px-3 py-1.5 text-end text-ink tabular-nums">
                      {format.number(day[series])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </Card>
  );
}

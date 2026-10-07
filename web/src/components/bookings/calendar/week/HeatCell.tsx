"use client";

import { formatLocalDate } from "@/components/insights/dates";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";

import { LEVEL_MIX, type LoadLevel } from "../_lib/weekLoad";
import { CLOSED_STYLE } from "../calendarStyles";

/** The colour of a level: the clay accent mixed into the surface (ink stays AA on every step). */
function levelBackground(level: LoadLevel): string {
  return level === 0 ? "var(--surface)" : `color-mix(in oklab, var(--accent-solid) ${LEVEL_MIX[level]}%, var(--surface))`;
}

/**
 * One place on one day of the week's heatmap: how full it is (the share,
 * or the rooms taken), how many bookings, coloured in five steps; hatched
 * when closed. A button that opens the day; one cell of the table is in
 * the tab order at a time (the arrows move between them).
 */
export function HeatCell({
  id,
  isActive,
  placeName,
  date,
  share,
  level,
  count,
  rooms,
  isTotal,
  onFocus,
  onOpen,
}: {
  id: string;
  isActive: boolean;
  placeName: string;
  date: string;
  share: number | null;
  level: LoadLevel;
  count: number;
  rooms: { booked: number; open: number } | null;
  isTotal: boolean;
  onFocus: () => void;
  onOpen: () => void;
}) {
  const { t, tp, locale } = useI18n();
  const isClosed = share === null;
  const percent = formatNumber(share ?? 0, locale, { style: "percent", maximumFractionDigits: 0 });
  const loadText = isClosed
    ? t("bookingCalendar.week.closed")
    : rooms
      ? tp("bookingCalendar.week.rooms", rooms.open, { booked: String(rooms.booked), open: String(rooms.open) })
      : count === 0
        ? t("bookingCalendar.week.free")
        : t("bookingCalendar.week.share", { percent });
  const countText = tp("bookings.count", count);
  return (
    <button
      type="button"
      data-heat-cell={id}
      tabIndex={isActive ? 0 : -1}
      onFocus={onFocus}
      onClick={onOpen}
      aria-label={t("bookingCalendar.week.cell", {
        place: placeName,
        date: formatLocalDate(date, locale, { weekday: "long", day: "numeric", month: "long" }),
        load: loadText,
        count: countText,
      })}
      style={isClosed ? CLOSED_STYLE : { backgroundColor: levelBackground(level) }}
      className={cn(
        "flex h-14 w-full cursor-pointer flex-col items-center justify-center rounded-lg border text-ink transition-[transform,box-shadow] duration-150 hover:-translate-y-px hover:shadow-md",
        isClosed ? "border-line bg-surface-muted text-ink-subtle" : "border-line/70",
        isTotal && "font-semibold",
      )}
    >
      <span className="text-sm font-semibold tabular-nums">{isClosed ? t("bookingCalendar.week.closed") : rooms ? `${rooms.booked}/${rooms.open}` : percent}</span>
      {isClosed ? null : (
        // The muted ink keeps AA on the lighter steps only; the deeper ones take the full ink.
        <span className={cn("text-[11px] tabular-nums", level >= 3 ? "text-ink" : "text-ink-muted")}>{countText}</span>
      )}
    </button>
  );
}

/** The heatmap's scale, quiet to full. */
export function HeatLegend() {
  const { t } = useI18n();
  const levels: LoadLevel[] = [0, 1, 2, 3, 4];
  return (
    <div className="flex items-center gap-2 text-xs text-ink-muted">
      <span>{t("bookingCalendar.week.legendTitle")}:</span>
      <span>{t("bookingCalendar.week.quiet")}</span>
      <span aria-hidden className="flex gap-1">
        {levels.map((level) => (
          <span key={level} className="size-3.5 rounded border border-line/70" style={{ backgroundColor: levelBackground(level) }} />
        ))}
      </span>
      <span>{t("bookingCalendar.week.full")}</span>
    </div>
  );
}

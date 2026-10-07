"use client";

import { IconPlus } from "@/components/icons";
import { UserContent } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";

import type { GridPlace } from "../_lib/calendarTypes";

/**
 * A place's column head (it stays in view while the hours scroll): its
 * name, how full it is today and how many bookings, a thin load bar, and
 * "+" for a new booking there (the keyboard's way to add one).
 */
export function DayColumnHeader({
  place,
  load,
  onCreate,
}: {
  place: GridPlace;
  load: { share: number | null; count: number };
  onCreate: () => void;
}) {
  const { t, tp, locale } = useI18n();
  const isClosed = load.share === null;
  const percent = formatNumber(load.share ?? 0, locale, { style: "percent", maximumFractionDigits: 0 });
  return (
    <div className="sticky top-0 z-30 flex items-start gap-2 border-e border-b border-line bg-surface px-3 py-2 last:border-e-0">
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-ink">
          <UserContent>{place.name}</UserContent>
        </p>
        <p className="truncate text-xs text-ink-subtle tabular-nums">
          {isClosed
            ? t("bookingCalendar.day.closedDay")
            : `${t("bookingCalendar.day.booked", { percent })} · ${tp("bookings.count", load.count)}`}
        </p>
        <div aria-hidden className="mt-1.5 h-1 overflow-hidden rounded-full bg-surface-muted">
          <div
            className={cn("h-full rounded-full bg-accent-solid transition-[width] duration-300", isClosed && "bg-line")}
            style={{ width: `${Math.round((load.share ?? 0) * 100)}%` }}
          />
        </div>
      </div>
      <button
        type="button"
        onClick={onCreate}
        aria-label={t("bookingCalendar.day.newAt", { place: place.name })}
        className="grid size-7 shrink-0 cursor-pointer place-items-center rounded-lg text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink"
      >
        <IconPlus className="size-4" aria-hidden />
      </button>
    </div>
  );
}

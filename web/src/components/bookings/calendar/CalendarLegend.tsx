"use client";

import { BOOKING_STATUS } from "@/components/insights/labels";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { SHOWN_STATUSES, STATUS_STYLE } from "./calendarStyles";

/** What the colours of the bookings mean, and how to move one. */
export function CalendarLegend({ hintId, showHint }: { hintId: string; showHint: boolean }) {
  const { t } = useI18n();
  return (
    <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-2 text-xs text-ink-muted">
      <ul aria-label={t("bookingCalendar.legend")} className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
        {SHOWN_STATUSES.map((status) => (
          <li key={status} className="flex items-center gap-1.5">
            <span aria-hidden className={cn("size-2.5 rounded-full", STATUS_STYLE[status].mark)} />
            {t(BOOKING_STATUS[status].label)}
          </li>
        ))}
      </ul>
      <p id={hintId} className={cn("max-w-prose text-ink-subtle", !showHint && "sr-only")}>
        {t("bookingCalendar.moveHint")}
      </p>
    </div>
  );
}

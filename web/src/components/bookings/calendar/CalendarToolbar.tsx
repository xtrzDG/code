"use client";

import { IconChevronRight } from "@/components/icons";
import { formatLocalDate, formatLocalDateRange, isLocalDate } from "@/components/insights/dates";
import { buttonClasses, Checkbox, DateField } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { shiftAnchor } from "./_lib/calendarDates";
import type { CalendarView } from "./_lib/calendarTypes";

const ARROW = cn(buttonClasses({ variant: "secondary", size: "sm" }), "w-8 justify-center px-0");

/**
 * The calendar's dates: back and on (a day, or a week), Today, the date
 * picker (the cabinet's DateField), what is shown as a heading, and the
 * test bookings switch.
 */
export function CalendarToolbar({
  headingId,
  view,
  anchor,
  window,
  today,
  includeTest,
  onAnchor,
  onIncludeTest,
}: {
  headingId: string;
  view: CalendarView;
  anchor: string;
  window: { from: string; to: string };
  today: string;
  includeTest: boolean;
  onAnchor: (date: string) => void;
  onIncludeTest: (include: boolean) => void;
}) {
  const { t, locale } = useI18n();
  const showsToday = window.from <= today && today <= window.to;
  const heading =
    view === "day"
      ? formatLocalDate(anchor, locale, { weekday: "long", day: "numeric", month: "long", year: "numeric" })
      : formatLocalDateRange(window.from, window.to, locale);
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
      <div role="group" aria-label={t("bookingCalendar.toolbar.label")} className="flex items-center gap-1">
        <button type="button" className={ARROW} aria-label={t(`bookingCalendar.toolbar.previous.${view}`)} onClick={() => onAnchor(shiftAnchor(view, anchor, -1))}>
          <IconChevronRight className="size-4 rotate-180 rtl:rotate-0" aria-hidden />
        </button>
        <button
          type="button"
          className={buttonClasses({ variant: "secondary", size: "sm" })}
          disabled={showsToday}
          onClick={() => onAnchor(today)}
        >
          {t("bookingCalendar.toolbar.today")}
        </button>
        <button type="button" className={ARROW} aria-label={t(`bookingCalendar.toolbar.next.${view}`)} onClick={() => onAnchor(shiftAnchor(view, anchor, 1))}>
          <IconChevronRight className="size-4 rtl:rotate-180" aria-hidden />
        </button>
      </div>
      <h2 id={headingId} className="min-w-0 text-base font-semibold text-ink first-letter:uppercase">
        {heading}
      </h2>
      <div className="flex w-full flex-wrap items-center gap-x-4 gap-y-2 sm:ms-auto sm:w-auto">
        <DateField
          aria-label={t("bookingCalendar.toolbar.date")}
          value={anchor}
          today={today}
          onChange={(value) => {
            if (isLocalDate(value)) {
              onAnchor(value);
            }
          }}
          className="w-44"
        />
        <Checkbox
          label={t("bookingCalendar.toolbar.includeTest")}
          checked={includeTest}
          onChange={(event) => onIncludeTest(event.target.checked)}
          className="items-center"
        />
      </div>
    </div>
  );
}

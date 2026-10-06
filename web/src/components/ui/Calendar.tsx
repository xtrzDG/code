"use client";

/**
 * A month to pick a day from, in the cabinet's language and with its week
 * start (Monday in Russian and Georgian, Sunday in English): the date
 * picker dialog pattern of WAI-ARIA. Arrows move by a day and a week,
 * Home and End to the ends of the week, Page Up and Page Down by a month
 * (with Shift by a year), Enter picks, Escape closes. Days outside
 * `min`…`max` cannot be picked.
 */

import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";

import { IconChevronRight } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import {
  addDaysIso,
  addMonthsIso,
  clampIso,
  dateText,
  isIsoDate,
  isoParts,
  isWithin,
  monthTitle,
  monthWeeks,
  weekColumns,
  type IsoDate,
} from "@/lib/dateInput";
import { weekdayName } from "@/lib/format";

import { Button } from "./Button";

const NAV_BUTTON =
  "inline-flex size-9 items-center justify-center rounded-lg text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink " +
  "focus-visible:outline-2 focus-visible:outline-focus disabled:cursor-not-allowed disabled:opacity-40";

export function Calendar({
  value,
  today,
  min,
  max,
  onSelect,
  onClear,
  onEscape,
}: {
  value: string;
  today: IsoDate;
  min?: string;
  max?: string;
  onSelect: (date: IsoDate) => void;
  /** Offered when the date may be empty (a filter). */
  onClear?: () => void;
  onEscape: () => void;
}) {
  const { t, locale } = useI18n();
  const titleId = useId();
  const grid = useRef<HTMLTableElement>(null);
  const [focused, setFocused] = useState<IsoDate>(() => clampIso(isIsoDate(value) ? value : today, min, max));
  const moveFocus = useRef(true);
  const shown = isoParts(focused) ?? { year: 2026, month: 1, day: 1 };
  const columns = weekColumns(locale);
  const weeks = monthWeeks(shown.year, shown.month, columns[0] ?? 1);
  const firstOfMonth = `${String(shown.year).padStart(4, "0")}-${String(shown.month).padStart(2, "0")}-01`;
  const canGoBack = !min || addDaysIso(firstOfMonth, -1) >= min;
  const canGoForward = !max || addMonthsIso(firstOfMonth, 1) <= max;

  useEffect(() => {
    if (moveFocus.current) {
      moveFocus.current = false;
      grid.current?.querySelector<HTMLButtonElement>(`[data-date="${focused}"]`)?.focus();
    }
  }, [focused]);

  const go = (next: IsoDate, withFocus: boolean) => {
    moveFocus.current = withFocus;
    setFocused(clampIso(next, min, max));
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTableElement>) => {
    const isRtl = getComputedStyle(event.currentTarget).direction === "rtl";
    const column = columns.indexOf(isoWeekday(focused));
    const moves: Record<string, () => IsoDate> = {
      ArrowRight: () => addDaysIso(focused, isRtl ? -1 : 1),
      ArrowLeft: () => addDaysIso(focused, isRtl ? 1 : -1),
      ArrowDown: () => addDaysIso(focused, 7),
      ArrowUp: () => addDaysIso(focused, -7),
      Home: () => addDaysIso(focused, -column),
      End: () => addDaysIso(focused, 6 - column),
      PageUp: () => addMonthsIso(focused, event.shiftKey ? -12 : -1),
      PageDown: () => addMonthsIso(focused, event.shiftKey ? 12 : 1),
    };
    const move = moves[event.key];
    if (move) {
      event.preventDefault();
      go(move(), true);
    } else if (event.key === "Escape") {
      // Inside a dialog Escape closes only the calendar.
      event.preventDefault();
      event.stopPropagation();
      onEscape();
    }
  };

  return (
    <div className="w-[18.5rem] max-w-[calc(100vw-2rem)] space-y-2">
      <div className="flex items-center justify-between gap-2">
        <button
          type="button"
          className={NAV_BUTTON}
          aria-label={t("formFields.date.previousMonth")}
          disabled={!canGoBack}
          onClick={() => go(addMonthsIso(focused, -1), false)}
        >
          <IconChevronRight className="size-4 rotate-180 rtl:rotate-0" aria-hidden />
        </button>
        <p id={titleId} aria-live="polite" className="text-sm font-semibold text-ink">
          {monthTitle(shown.year, shown.month, locale)}
        </p>
        <button
          type="button"
          className={NAV_BUTTON}
          aria-label={t("formFields.date.nextMonth")}
          disabled={!canGoForward}
          onClick={() => go(addMonthsIso(focused, 1), false)}
        >
          <IconChevronRight className="size-4 rtl:rotate-180" aria-hidden />
        </button>
      </div>
      <table ref={grid} role="grid" aria-labelledby={titleId} className="w-full border-collapse text-center" onKeyDown={onKeyDown}>
        <thead>
          <tr>
            {columns.map((weekday) => (
              <th key={weekday} scope="col" abbr={weekdayName(weekday, locale)} className="pb-1 text-xs font-medium text-ink-subtle">
                {weekdayName(weekday, locale, "short")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {weeks.map((week) => (
            <tr key={week.find(Boolean) ?? "empty"}>
              {week.map((day, index) =>
                day === null ? (
                  <td key={`empty-${index}`} />
                ) : (
                  <td key={day} role="gridcell" aria-selected={day === value} className="p-0.5">
                    <button
                      type="button"
                      data-date={day}
                      tabIndex={day === focused ? 0 : -1}
                      aria-label={dateText(day, locale, "full")}
                      aria-current={day === today ? "date" : undefined}
                      aria-disabled={isWithin(day, min, max) ? undefined : true}
                      onClick={() => (isWithin(day, min, max) ? onSelect(day) : undefined)}
                      onFocus={() => setFocused(day)}
                      className={cn(
                        "inline-flex size-9 items-center justify-center rounded-lg text-sm tabular-nums transition-colors",
                        "focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-focus",
                        day === value
                          ? "bg-accent-solid font-semibold text-on-accent"
                          : day === today
                            ? "font-semibold text-accent ring-1 ring-accent/40 ring-inset hover:bg-accent-soft"
                            : "text-ink hover:bg-surface-muted",
                        !isWithin(day, min, max) && "cursor-not-allowed text-ink-subtle/50 hover:bg-transparent",
                      )}
                    >
                      {Number(day.slice(8))}
                    </button>
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex items-center justify-between gap-2 border-t border-line pt-2">
        <Button variant="ghost" size="sm" disabled={!isWithin(today, min, max)} onClick={() => onSelect(today)}>
          {t("formFields.date.today")}
        </Button>
        {onClear ? (
          <Button variant="ghost" size="sm" onClick={onClear}>
            {t("formFields.date.clear")}
          </Button>
        ) : null}
      </div>
    </div>
  );
}

/** ISO weekday (1 = Monday) of an ISO date. */
function isoWeekday(date: IsoDate): 1 | 2 | 3 | 4 | 5 | 6 | 7 {
  const parts = isoParts(date) ?? { year: 2026, month: 1, day: 1 };
  const day = new Date(Date.UTC(parts.year, parts.month - 1, parts.day)).getUTCDay();
  return (day === 0 ? 7 : day) as 1 | 2 | 3 | 4 | 5 | 6 | 7;
}

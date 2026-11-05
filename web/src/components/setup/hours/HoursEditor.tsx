"use client";

import type { OpeningInterval, Weekday } from "@/api/types";
import { IconPlus, IconTrash } from "@/components/icons";
import { Button, Checkbox, TimeField } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { formatMinutesOfDay, parseTimeOfDay, weekdayName } from "@/lib/format";
import { timeText } from "@/lib/timeInput";
import {
  intervalsToWeek,
  isOvernight,
  isRoundTheClock,
  overlappingWeekdays,
  weekToIntervals,
  type DayHours,
} from "@/lib/hours";

export interface TimeRow {
  key: string;
  opens: string;
  closes: string;
}

export interface DayRows {
  weekday: Weekday;
  rows: TimeRow[];
}

const DEFAULT_OPENS = "09:00";
const DEFAULT_CLOSES = "18:00";

let rowSequence = 0;
function nextRowKey(): string {
  rowSequence += 1;
  return `hours-${rowSequence}`;
}

/** Editor rows from the API's opening intervals. */
export function hoursToRows(hours: readonly OpeningInterval[]): DayRows[] {
  return intervalsToWeek(hours).map((day) => ({
    weekday: day.weekday,
    rows: day.intervals.map((interval) => ({
      key: nextRowKey(),
      opens: formatMinutesOfDay(interval.opens),
      closes: formatMinutesOfDay(interval.closes),
    })),
  }));
}

/** API intervals from the editor, or per-day problems to show. */
export function rowsToHours(
  days: readonly DayRows[],
): { ok: true; hours: OpeningInterval[] } | { ok: false; errors: Partial<Record<Weekday, MessageKey>> } {
  const errors: Partial<Record<Weekday, MessageKey>> = {};
  const week: DayHours[] = days.map((day) => ({
    weekday: day.weekday,
    intervals: day.rows.flatMap((row) => {
      const opens = parseTimeOfDay(row.opens);
      const closes = parseTimeOfDay(row.closes);
      if (opens === null || closes === null) {
        errors[day.weekday] = "validation.time";
        return [];
      }
      return [{ opens, closes }];
    }),
  }));
  if (Object.keys(errors).length > 0) {
    return { ok: false, errors };
  }
  const hours = weekToIntervals(week);
  const overlapping = overlappingWeekdays(hours);
  if (overlapping.length > 0) {
    for (const weekday of overlapping) {
      errors[weekday] = "validation.hoursOverlap";
    }
    return { ok: false, errors };
  }
  return { ok: true, hours };
}

/**
 * Weekly opening hours: each day closed or open with one or more intervals.
 * A closing time at or before the opening time runs past midnight.
 */
export function HoursEditor({
  days,
  onChange,
  errors,
}: {
  days: DayRows[];
  onChange: (days: DayRows[]) => void;
  errors: Partial<Record<Weekday, MessageKey>>;
}) {
  const { t, locale } = useI18n();

  const updateDay = (weekday: Weekday, rows: TimeRow[]) =>
    onChange(days.map((day) => (day.weekday === weekday ? { ...day, rows } : day)));

  const copyFirstDayToAll = () => {
    const first = days[0];
    if (!first) {
      return;
    }
    onChange(days.map((day) => ({ ...day, rows: first.rows.map((row) => ({ ...row, key: nextRowKey() })) })));
  };

  return (
    <div className="space-y-3">
      <ul className="divide-y divide-line rounded-xl border border-line">
        {days.map((day) => {
          const dayName = weekdayName(day.weekday, locale);
          const isOpen = day.rows.length > 0;
          const error = errors[day.weekday];
          return (
            <li key={day.weekday} className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-start">
              <div className="flex items-center justify-between gap-3 sm:w-44 sm:pt-2">
                <Checkbox
                  id={`day-${day.weekday}`}
                  checked={isOpen}
                  onChange={(event) =>
                    updateDay(
                      day.weekday,
                      event.target.checked ? [{ key: nextRowKey(), opens: DEFAULT_OPENS, closes: DEFAULT_CLOSES }] : [],
                    )
                  }
                  label={<span className="font-medium capitalize">{dayName}</span>}
                />
                {!isOpen ? <span className="text-sm text-ink-subtle sm:hidden">{t("onboarding.week.closed")}</span> : null}
              </div>
              <div className="min-w-0 flex-1 space-y-2">
                {!isOpen ? (
                  <p className="hidden pt-2 text-sm text-ink-subtle sm:block">{t("onboarding.week.closed")}</p>
                ) : (
                  day.rows.map((row, index) => {
                    const opens = parseTimeOfDay(row.opens);
                    const closes = parseTimeOfDay(row.closes);
                    const interval = opens !== null && closes !== null ? { opens, closes } : null;
                    return (
                      <div key={row.key} className="flex flex-wrap items-center gap-2">
                        <TimeField
                          aria-label={`${dayName}: ${t("onboarding.week.opens")}`}
                          aria-invalid={error ? true : undefined}
                          value={row.opens}
                          step={30}
                          onChange={(opens) =>
                            updateDay(
                              day.weekday,
                              day.rows.map((item) => (item.key === row.key ? { ...item, opens } : item)),
                            )
                          }
                          className="w-32"
                        />
                        <span className="text-ink-subtle" aria-hidden>
                          –
                        </span>
                        <TimeField
                          aria-label={`${dayName}: ${t("onboarding.week.closes")}`}
                          aria-invalid={error ? true : undefined}
                          value={row.closes}
                          step={30}
                          defaultTime={DEFAULT_CLOSES}
                          onChange={(closes) =>
                            updateDay(
                              day.weekday,
                              day.rows.map((item) => (item.key === row.key ? { ...item, closes } : item)),
                            )
                          }
                          className="w-32"
                        />
                        {interval && isRoundTheClock(interval) ? (
                          <span className="text-sm text-ink-muted">{t("onboarding.week.roundTheClock")}</span>
                        ) : interval && isOvernight(interval) ? (
                          <span className="text-sm text-ink-muted">
                            {t("onboarding.week.overnight", { time: timeText(interval.closes, locale) })}
                          </span>
                        ) : null}
                        <div className="ms-auto flex gap-1">
                          {index === day.rows.length - 1 ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              aria-label={`${dayName}: ${t("onboarding.week.addInterval")}`}
                              title={t("onboarding.week.addInterval")}
                              onClick={() =>
                                updateDay(day.weekday, [...day.rows, { key: nextRowKey(), opens: "", closes: "" }])
                              }
                            >
                              <IconPlus className="size-4" aria-hidden />
                            </Button>
                          ) : null}
                          <Button
                            variant="ghost"
                            size="sm"
                            aria-label={`${dayName}: ${t("onboarding.week.removeInterval")}`}
                            title={t("onboarding.week.removeInterval")}
                            onClick={() => updateDay(day.weekday, day.rows.filter((item) => item.key !== row.key))}
                          >
                            <IconTrash className="size-4" aria-hidden />
                          </Button>
                        </div>
                      </div>
                    );
                  })
                )}
                {error ? <p className="text-sm text-danger">{t(error)}</p> : null}
              </div>
            </li>
          );
        })}
      </ul>
      <Button variant="ghost" size="sm" onClick={copyFirstDayToAll}>
        {t("onboarding.week.copyToAll")}
      </Button>
    </div>
  );
}

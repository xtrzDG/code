"use client";

import { useRef, useState, type KeyboardEvent } from "react";

import { formatLocalDate } from "@/components/insights/dates";
import { UserContent } from "@/components/ui";
import { localeDirection } from "@/i18n/config";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { formatDateSpan } from "../_lib/calendarDates";
import type { CalendarGrid, CalendarView, GridPlace } from "../_lib/calendarTypes";
import { dayLoad, loadLevel, placeDayShare, type LoadLevel } from "../_lib/weekLoad";
import { HeatCell, HeatLegend } from "./HeatCell";

interface HeatRow {
  key: string;
  place: GridPlace | null;
}

/**
 * The week at a glance (Bookings → Week): every place by day, coloured by
 * how full it is (minutes for tables and masters, rooms for nights), with
 * the whole business's day on top. A cell opens that day (or its nights);
 * the arrow keys move between cells, Home and End along a row.
 */
export function WeekHeatmap({
  grid,
  today,
  onOpenDay,
}: {
  grid: CalendarGrid;
  today: string;
  onOpenDay: (date: string, view: CalendarView) => void;
}) {
  const { t, locale } = useI18n();
  const tableRef = useRef<HTMLTableElement>(null);
  const [active, setActive] = useState({ row: 0, column: 0 });
  const rows: HeatRow[] = [{ key: "all", place: null }, ...grid.places.map((place) => ({ key: place.id, place }))];
  const onlyRooms = grid.places.length > 0 && grid.places.every((place) => place.booking_unit === "night");
  const forward = localeDirection(locale) === "rtl" ? "ArrowLeft" : "ArrowRight";

  const focusCell = (row: number, column: number) => {
    setActive({ row, column });
    tableRef.current?.querySelector<HTMLElement>(`[data-heat-cell="${row}-${column}"]`)?.focus();
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTableElement>) => {
    const steps: Record<string, [number, number]> = {
      ArrowUp: [-1, 0],
      ArrowDown: [1, 0],
      [forward]: [0, 1],
      [forward === "ArrowRight" ? "ArrowLeft" : "ArrowRight"]: [0, -1],
    };
    const lastColumn = grid.days.length - 1;
    const step = steps[event.key];
    if (step) {
      event.preventDefault();
      focusCell(Math.min(Math.max(active.row + step[0], 0), rows.length - 1), Math.min(Math.max(active.column + step[1], 0), lastColumn));
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      focusCell(active.row, event.key === "Home" ? 0 : lastColumn);
    }
  };

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto rounded-2xl border border-line bg-surface p-2">
        <table
          ref={tableRef}
          onKeyDown={onKeyDown}
          aria-label={t("bookingCalendar.week.label", { range: formatDateSpan(grid.date_from, grid.date_to, locale) })}
          className="w-full min-w-[38rem] table-fixed border-separate border-spacing-1 sm:min-w-[42rem]"
        >
          <thead>
            <tr>
              <th scope="col" className="sticky start-0 z-10 w-28 bg-surface px-2 text-start text-xs font-medium text-ink-subtle sm:w-44">
                {t("bookingCalendar.week.place")}
              </th>
              {grid.days.map((day) => (
                <th
                  key={day.date}
                  scope="col"
                  className={cn("rounded-lg px-1 py-1 text-xs font-medium", day.date === today ? "bg-accent-soft text-accent-ink" : "text-ink-muted")}
                >
                  <span className="block text-[10px] tracking-wide uppercase">{formatLocalDate(day.date, locale, { weekday: "short" })}</span>
                  <span className="block font-semibold tabular-nums">{formatLocalDate(day.date, locale, { day: "numeric", month: "short" })}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={row.key}>
                <th scope="row" className="sticky start-0 z-10 truncate bg-surface px-2 text-start text-sm font-semibold text-ink">
                  {row.place ? <UserContent>{row.place.name}</UserContent> : t("bookingCalendar.week.allPlaces")}
                </th>
                {grid.days.map((day, columnIndex) => {
                  const placeDay = row.place ? day.places.find((item) => item.resource_id === row.place?.id) : undefined;
                  const load = placeDay ? { share: placeDayShare(placeDay), count: placeDay.booking_count } : dayLoad(day);
                  const level: LoadLevel = loadLevel(load.share);
                  const isNights = row.place ? row.place.booking_unit === "night" : onlyRooms;
                  return (
                    <td key={day.date} className="p-0">
                      <HeatCell
                        id={`${rowIndex}-${columnIndex}`}
                        isActive={active.row === rowIndex && active.column === columnIndex}
                        placeName={row.place?.name ?? t("bookingCalendar.week.allPlaces")}
                        date={day.date}
                        share={load.share}
                        level={level}
                        count={load.count}
                        rooms={placeDay?.open_units !== null && placeDay?.open_units !== undefined ? { booked: placeDay.booked_units ?? 0, open: placeDay.open_units } : null}
                        isTotal={row.place === null}
                        onFocus={() => setActive({ row: rowIndex, column: columnIndex })}
                        onOpen={() => onOpenDay(day.date, isNights ? "nights" : "day")}
                      />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <HeatLegend />
    </div>
  );
}

"use client";

import type { ComponentProps, MouseEvent, PointerEvent } from "react";

import type { BookingView } from "@/components/insights/types";
import type { PartyWording } from "@/components/insights/usePartyWording";
import { useI18n } from "@/i18n/client";
import { formatLocalTime } from "@/components/insights/dates";

import { durationOf } from "../_lib/calendarMoves";
import type { GridOpenRange, GridPlace } from "../_lib/calendarTypes";
import { minuteOfTime, timeOfMinute, type Laned, type Span } from "../_lib/dayLayout";
import { CLOSED_STYLE } from "../calendarStyles";
import type { Locate, MovePreview } from "../useMoveGestures";
import { BlockGhost, BookingBlock } from "./BookingBlock";
import { HOUR_HEIGHT, MINUTE_HEIGHT, minuteAtClick } from "./dayLocate";

/** Hour lines every hour, a fainter one at each half hour. */
const HOUR_LINES = {
  backgroundImage: `linear-gradient(to bottom, var(--line) 1px, transparent 1px), linear-gradient(to bottom, color-mix(in oklab, var(--line) 55%, transparent) 1px, transparent 1px)`,
  backgroundSize: `100% ${HOUR_HEIGHT}px, 100% ${HOUR_HEIGHT / 2}px`,
};

/** The ghost of the booking being moved, when it would land on this column. */
function ghostOn(placeId: string, date: string, preview: MovePreview | null): Laned<BookingView> | null {
  if (!preview || preview.target.resourceId !== placeId || preview.target.date !== date || preview.target.time === null) {
    return null;
  }
  const start = minuteOfTime(preview.target.time) ?? 0;
  return { item: { ...preview.booking, time: preview.target.time, end_time: timeOfMinute(start + durationOf(preview.booking)) }, span: { start, end: Math.min(start + durationOf(preview.booking), 1440) }, lane: 0, lanes: 1 };
}

/**
 * One place on the day: its open hours on a hatched closed background,
 * hour lines, the "now" line today, its bookings in lanes and the preview
 * of a booking being moved here. A click on free space starts a new
 * booking there, at that quarter of an hour.
 */
export function DayColumn({
  place,
  date,
  axis,
  openRanges,
  laned,
  preview,
  nowMinute,
  hintId,
  party,
  onOpen,
  onCreate,
  movable,
  locator,
}: {
  place: GridPlace;
  date: string;
  axis: Span;
  openRanges: readonly GridOpenRange[];
  laned: readonly Laned<BookingView>[];
  preview: MovePreview | null;
  nowMinute: number | null;
  hintId: string;
  party: PartyWording;
  onOpen: (booking: BookingView) => void;
  onCreate: (initial: { date: string; time: string; resourceId: string }) => void;
  movable: (booking: BookingView, makeLocate: (event: PointerEvent<HTMLElement>) => Locate) => Partial<ComponentProps<"button">>;
  locator: (booking: BookingView) => (event: PointerEvent<HTMLElement>) => Locate;
}) {
  const { t, locale } = useI18n();
  const height = (axis.end - axis.start) * MINUTE_HEIGHT;
  const ghost = ghostOn(place.id, date, preview);

  const create = (event: MouseEvent<HTMLDivElement>) => {
    if ((event.target as HTMLElement).closest("[data-calendar-booking]")) {
      return;
    }
    const minute = minuteAtClick(event.clientY, event.currentTarget, axis);
    onCreate({ date, time: timeOfMinute(minute), resourceId: place.id });
  };

  return (
    <div
      data-calendar-column={place.id}
      data-place-name={place.name}
      onClick={create}
      className="relative cursor-cell border-e border-line bg-surface-muted last:border-e-0"
      style={{ height, ...CLOSED_STYLE }}
    >
      {openRanges.map((range) => (
        <div
          key={`${range.opens_at}-${range.closes_at}`}
          aria-hidden
          className="absolute inset-x-0 bg-surface"
          style={{ top: (Math.max(range.opens_at, axis.start) - axis.start) * MINUTE_HEIGHT, height: (Math.min(range.closes_at, axis.end) - Math.max(range.opens_at, axis.start)) * MINUTE_HEIGHT }}
        />
      ))}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={HOUR_LINES}
      />
      {nowMinute !== null && nowMinute >= axis.start && nowMinute <= axis.end ? (
        <div
          aria-hidden
          data-calendar-now=""
          className="pointer-events-none absolute inset-x-0 z-20 h-0.5 bg-accent-solid"
          style={{ top: (nowMinute - axis.start) * MINUTE_HEIGHT }}
          title={t("bookingCalendar.day.now", { time: formatLocalTime(timeOfMinute(nowMinute), locale) })}
        />
      ) : null}
      {laned.map((entry) => (
        <BookingBlock
          key={entry.item.id}
          laned={entry}
          axisStart={axis.start}
          hintId={hintId}
          party={party}
          isMoving={preview?.booking.id === entry.item.id}
          onOpen={onOpen}
          movable={movable(entry.item, locator(entry.item))}
        />
      ))}
      {ghost ? <BlockGhost laned={ghost} axisStart={axis.start} /> : null}
    </div>
  );
}

/** The hours down the side of the grid, in the locale's clock. */
export function TimeGutter({ axis }: { axis: Span }) {
  const { locale } = useI18n();
  const hours: number[] = [];
  for (let minute = Math.ceil(axis.start / 60) * 60; minute < axis.end; minute += 60) {
    hours.push(minute);
  }
  return (
    <div aria-hidden className="sticky start-0 z-20 border-e border-line bg-surface" style={{ height: (axis.end - axis.start) * MINUTE_HEIGHT }}>
      {hours.map((minute) => (
        <span
          key={minute}
          className="absolute end-1.5 -translate-y-1/2 text-[11px] text-ink-subtle tabular-nums first:translate-y-0.5"
          style={{ top: (minute - axis.start) * MINUTE_HEIGHT }}
        >
          {formatLocalTime(timeOfMinute(minute), locale)}
        </span>
      ))}
    </div>
  );
}

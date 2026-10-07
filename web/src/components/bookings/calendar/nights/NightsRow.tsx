"use client";

import type { ComponentProps, PointerEvent } from "react";

import { BOOKING_STATUS } from "@/components/insights/labels";
import { daysBetween, formatLocalDate, formatLocalDateRange } from "@/components/insights/dates";
import type { BookingView } from "@/components/insights/types";
import { UserContent } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import type { GridPlace, GridPlaceDay } from "../_lib/calendarTypes";
import type { Laned } from "../_lib/dayLayout";
import type { StayNights } from "../_lib/nightsLayout";
import { CLOSED_STYLE, GHOST_CLASS, STATUS_STYLE } from "../calendarStyles";
import type { Locate } from "../useMoveGestures";

/** One lane of stays is this tall. */
const LANE_HEIGHT = "2.375rem";

export interface ShownStay {
  laned: Laned<BookingView>;
  nights: StayNights;
}

/**
 * One room (or room type with several rooms) across the nights: each night
 * a cell that starts a new stay there (with how many rooms are taken), the
 * stays as bars over the nights they take, one lane per room, and the bar
 * of a stay being moved here. A bar is a button: open it, drag it to
 * another night or room, or move it with the arrows and Enter.
 */
export function NightsRow({
  room,
  dates,
  placeDays,
  stays,
  lanes,
  ghost,
  movingId,
  template,
  hintId,
  onOpen,
  onCreate,
  movable,
  locator,
}: {
  room: GridPlace;
  dates: readonly string[];
  placeDays: readonly (GridPlaceDay | undefined)[];
  stays: readonly ShownStay[];
  lanes: number;
  ghost: StayNights | null;
  movingId: string | null;
  template: string;
  hintId: string;
  onOpen: (booking: BookingView) => void;
  onCreate: (date: string) => void;
  movable: (booking: BookingView, makeLocate: (event: PointerEvent<HTMLElement>) => Locate) => Partial<ComponentProps<"button">>;
  locator: (booking: BookingView) => (event: PointerEvent<HTMLElement>) => Locate;
}) {
  const { t, tp, locale } = useI18n();
  const longDate = (date: string) => formatLocalDate(date, locale, { weekday: "short", day: "numeric", month: "long" });
  return (
    <div
      data-calendar-room={room.id}
      data-place-name={room.name}
      className="grid border-b border-line last:border-b-0"
      style={{ gridTemplateColumns: template, gridTemplateRows: `repeat(${lanes}, ${LANE_HEIGHT})` }}
    >
      <div className="sticky start-0 z-20 flex flex-col justify-center border-e border-line bg-surface px-3" style={{ gridRow: `1 / span ${lanes}` }}>
        <UserContent className="truncate text-sm font-semibold text-ink">{room.name}</UserContent>
        {room.unit_count > 1 ? <span className="text-xs text-ink-subtle tabular-nums">×{room.unit_count}</span> : null}
      </div>
      {dates.map((date, index) => {
        const placeDay = placeDays[index];
        const open = placeDay?.open_units ?? 0;
        const booked = placeDay?.booked_units ?? 0;
        const taken = t("bookingCalendar.nights.taken", { booked: String(booked), open: String(open) });
        const position = { gridColumn: index + 2, gridRow: `1 / span ${lanes}` };
        return open === 0 ? (
          <div
            key={date}
            title={t("bookingCalendar.week.closed")}
            className="border-e border-line bg-surface-muted last:border-e-0"
            style={{ ...position, ...CLOSED_STYLE }}
          />
        ) : (
          <button
            key={date}
            type="button"
            onClick={() => onCreate(date)}
            aria-label={`${t("bookingCalendar.nights.newStay", { place: room.name, date: longDate(date) })}. ${taken}`}
            className={cn(
              "flex cursor-cell items-end justify-end border-e border-line px-1 pb-0.5 text-[10px] text-ink-subtle tabular-nums transition-colors last:border-e-0 hover:bg-surface-muted",
              booked >= open && "bg-surface-muted/60",
            )}
            style={position}
          >
            <span aria-hidden>
              {booked}/{open}
            </span>
          </button>
        );
      })}
      {stays.map(({ laned, nights }) => {
        const booking = laned.item;
        const name = booking.contact_name ?? t("insights.unknownCustomer");
        return (
          <button
            key={booking.id}
            type="button"
            {...movable(booking, locator(booking))}
            onClick={() => onOpen(booking)}
            aria-label={t("bookingCalendar.block.label", {
              name,
              time: formatLocalDateRange(booking.date, booking.end_date, locale),
              place: booking.resource_name,
              status: t(BOOKING_STATUS[booking.status].label),
            })}
            aria-describedby={hintId}
            style={{ gridColumn: `${nights.first + 2} / span ${nights.count}`, gridRow: laned.lane + 1 }}
            className={cn(
              "relative z-10 my-0.5 flex min-w-0 cursor-grab items-center gap-1.5 overflow-hidden rounded-md border ps-3 pe-2 text-start text-xs shadow-sm",
              "touch-pan-x touch-pan-y select-none [-webkit-touch-callout:none] hover:shadow-md focus-visible:z-20 focus-visible:outline-2 focus-visible:-outline-offset-1 active:cursor-grabbing",
              STATUS_STYLE[booking.status].block,
              nights.startsBefore ? "ms-0 rounded-s-none" : "ms-1",
              nights.endsAfter ? "me-0 rounded-e-none" : "me-1",
              movingId === booking.id && "opacity-40",
            )}
          >
            <span aria-hidden className={cn("absolute inset-y-1 start-1 w-1 rounded-full", STATUS_STYLE[booking.status].mark)} />
            <UserContent className="truncate font-semibold text-ink">{name}</UserContent>
            <span className="shrink-0 text-ink-muted tabular-nums">{tp("bookings.nights", daysBetween(booking.date, booking.end_date))}</span>
          </button>
        );
      })}
      {ghost ? (
        <div
          aria-hidden
          data-calendar-ghost=""
          className={cn("z-30 mx-1 my-0.5 rounded-md shadow-lg", GHOST_CLASS)}
          style={{ gridColumn: `${ghost.first + 2} / span ${ghost.count}`, gridRow: 1 }}
        />
      ) : null}
    </div>
  );
}

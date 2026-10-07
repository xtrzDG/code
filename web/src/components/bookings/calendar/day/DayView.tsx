"use client";

import { useEffect, useId, useRef } from "react";

import { IconCalendar } from "@/components/icons";
import { formatLocalDate } from "@/components/insights/dates";
import type { BookingView } from "@/components/insights/types";
import { usePartyWording } from "@/components/insights/usePartyWording";
import { ButtonLink, EmptyState } from "@/components/ui";
import { useBusiness } from "@/components/business/BusinessContext";
import { localeDirection } from "@/i18n/config";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import type { CalendarGrid, MoveTarget } from "../_lib/calendarTypes";
import { daySpan, layoutLanes, placeLoad, SLOT_MINUTES, timeAxis, timeOfMinute, type Span } from "../_lib/dayLayout";
import { CalendarLegend } from "../CalendarLegend";
import { useMoveAnnouncement } from "../useMoveAnnouncement";
import { useMoveGestures } from "../useMoveGestures";
import { DayColumn, TimeGutter } from "./DayColumn";
import { DayColumnHeader } from "./DayColumnHeader";
import { dayLocator, MINUTE_HEIGHT } from "./dayLocate";


/**
 * One day by place (Bookings → Day): places booked by time are columns
 * and the rows are the hours they open (and any booking outside them).
 * Bookings are blocks coloured by status, side by side where they overlap;
 * drag one (or focus it and use the arrows, then Enter) to move it to
 * another time or place, with Undo. A click on free space starts a new
 * booking there. Today opens scrolled to now.
 */
export function DayView({
  grid,
  date,
  nowMinute,
  onOpen,
  onCreate,
  onMove,
}: {
  grid: CalendarGrid;
  date: string;
  /** The business's minute of the day when `date` is today; null otherwise. */
  nowMinute: number | null;
  onOpen: (booking: BookingView) => void;
  onCreate: (initial: { date: string; time: string; resourceId: string }) => void;
  onMove: (booking: BookingView, target: MoveTarget) => Promise<boolean>;
}) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const party = usePartyWording();
  const hintId = useId();
  const scrollRef = useRef<HTMLDivElement>(null);
  const nowRef = useRef(nowMinute);

  const day = grid.days.find((item) => item.date === date) ?? grid.days[0];
  const places = grid.places.filter((place) => place.booking_unit === "time_slot");
  const placeDays = new Map((day?.places ?? []).map((placeDay) => [placeDay.resource_id, placeDay]));
  const placeIds = new Set(places.map((place) => place.id));
  const entries = grid.bookings.flatMap((booking) => {
    const span = booking.status === "cancelled" || !placeIds.has(booking.resource_id) ? null : daySpan(booking, date);
    return span ? [{ item: booking, span }] : [];
  });
  const ranges = [...(day?.business_ranges ?? []), ...places.flatMap((place) => placeDays.get(place.id)?.open_ranges ?? [])];
  const axis: Span = timeAxis(ranges, entries.map((entry) => entry.span));
  const gestures = useMoveGestures({
    onMove,
    places: places.map((place) => ({ id: place.id, name: place.name })),
    bounds: { firstMinute: axis.start, lastMinute: axis.end - SLOT_MINUTES, firstDate: date, lastDate: date },
    forwardKey: localeDirection(locale) === "rtl" ? "ArrowLeft" : "ArrowRight",
  });
  const announcement = useMoveAnnouncement(gestures.preview, gestures.isCancelled);

  useEffect(() => {
    nowRef.current = nowMinute;
  });
  // A day opens at its first hour; today, a little above now.
  useEffect(() => {
    const element = scrollRef.current;
    const now = nowRef.current;
    if (element) {
      element.scrollTop = now === null ? 0 : Math.max((now - axis.start) * MINUTE_HEIGHT - element.clientHeight / 3, 0);
    }
  }, [date, axis.start]);

  if (places.length === 0) {
    return (
      <EmptyState
        icon={<IconCalendar className="size-6" />}
        title={t("bookingCalendar.day.noPlacesTitle")}
        description={t("bookingCalendar.day.noPlacesDescription")}
        action={
          <ButtonLink variant="secondary" href={`${businessPath(business.id, "assistant/knowledge")}/resources`}>
            {t("bookingCalendar.day.toPlaces")}
          </ButtonLink>
        }
      />
    );
  }

  const firstOpen = (placeId: string) => placeDays.get(placeId)?.open_ranges?.[0]?.opens_at ?? axis.start;
  const container = () => scrollRef.current;
  return (
    <div className="space-y-3">
      <div
        ref={scrollRef}
        role="region"
        tabIndex={-1}
        aria-label={t("bookingCalendar.day.label", { date: formatLocalDate(date, locale, { weekday: "long", day: "numeric", month: "long" }) })}
        data-calendar-day={date}
        className="relative max-h-[min(70vh,46rem)] overflow-auto overscroll-contain rounded-2xl border border-line bg-surface"
      >
        <div
          className="grid w-full"
          style={{ gridTemplateColumns: `4rem repeat(${places.length}, minmax(9rem, 1fr))`, minWidth: `calc(4rem + ${places.length} * 9rem)` }}
        >
          <div className="sticky start-0 top-0 z-40 border-e border-b border-line bg-surface" />
          {places.map((place) => {
            const placeDay = placeDays.get(place.id);
            const spans = entries.filter((entry) => entry.item.resource_id === place.id).map((entry) => entry.span);
            return (
              <DayColumnHeader
                key={place.id}
                place={place}
                load={placeDay ? placeLoad(placeDay, spans) : { share: null, count: spans.length }}
                onCreate={() => onCreate({ date, time: timeOfMinute(firstOpen(place.id)), resourceId: place.id })}
              />
            );
          })}
          <TimeGutter axis={axis} />
          {places.map((place) => (
            <DayColumn
              key={place.id}
              place={place}
              date={date}
              axis={axis}
              openRanges={placeDays.get(place.id)?.open_ranges ?? []}
              laned={layoutLanes(entries.filter((entry) => entry.item.resource_id === place.id))}
              preview={gestures.preview}
              nowMinute={nowMinute}
              hintId={hintId}
              party={party}
              onOpen={onOpen}
              onCreate={onCreate}
              movable={gestures.movable}
              locator={(booking) => dayLocator(container, booking, date, axis)}
            />
          ))}
        </div>
      </div>
      <CalendarLegend hintId={hintId} showHint={entries.length > 0} />
      <p className="sr-only" role="status" aria-live="polite">
        {announcement}
      </p>
    </div>
  );
}

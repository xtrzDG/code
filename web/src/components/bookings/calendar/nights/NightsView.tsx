"use client";

import { useId, useRef } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconCalendar } from "@/components/icons";
import { addDays, daysBetween, formatLocalDate, formatLocalDateRange } from "@/components/insights/dates";
import type { BookingView } from "@/components/insights/types";
import { ButtonLink, EmptyState } from "@/components/ui";
import { localeDirection } from "@/i18n/config";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { businessPath } from "@/lib/navigation";

import { windowDates } from "../_lib/calendarDates";
import type { CalendarGrid, MoveTarget } from "../_lib/calendarTypes";
import { layoutStays, stayNights } from "../_lib/nightsLayout";
import { CalendarLegend } from "../CalendarLegend";
import { useMoveAnnouncement } from "../useMoveAnnouncement";
import { useMoveGestures, type MovePreview } from "../useMoveGestures";
import { nightsLocator } from "./nightsLocate";
import { NightsRow, type ShownStay } from "./NightsRow";

/** The nights the moved stay would take on this room's row, cut to the window. */
function ghostFor(roomId: string, preview: MovePreview | null, from: string, days: number) {
  if (!preview || preview.target.resourceId !== roomId || preview.target.time !== null) {
    return null;
  }
  const nights = Math.max(daysBetween(preview.booking.date, preview.booking.end_date), 1);
  return stayNights({ date: preview.target.date, end_date: addDays(preview.target.date, nights) }, from, days);
}

/**
 * Rooms by night (Bookings → Nights, for hotels and guest houses): every
 * room booked by the night is a row, two weeks of nights are the columns,
 * each stay a bar over its nights. A free night starts a new stay there;
 * a stay moves to another room or date by drag, or by the arrow keys
 * (a night left or right, a room up or down) and Enter, with Undo.
 */
export function NightsView({
  grid,
  today,
  onOpen,
  onCreate,
  onMove,
}: {
  grid: CalendarGrid;
  today: string;
  onOpen: (booking: BookingView) => void;
  onCreate: (initial: { date: string; resourceId: string }) => void;
  onMove: (booking: BookingView, target: MoveTarget) => Promise<boolean>;
}) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const hintId = useId();
  const scrollRef = useRef<HTMLDivElement>(null);
  const from = grid.date_from;
  const dates = windowDates(from, grid.days.length);
  const rooms = grid.places.filter((place) => place.booking_unit === "night");
  const gestures = useMoveGestures({
    onMove,
    places: rooms.map((room) => ({ id: room.id, name: room.name })),
    bounds: { firstMinute: 0, lastMinute: 0, firstDate: from, lastDate: grid.date_to },
    forwardKey: localeDirection(locale) === "rtl" ? "ArrowLeft" : "ArrowRight",
    moves: "nights",
  });
  const announcement = useMoveAnnouncement(gestures.preview, gestures.isCancelled);

  if (rooms.length === 0) {
    return (
      <EmptyState
        icon={<IconCalendar className="size-6" />}
        title={t("bookingCalendar.nights.noRoomsTitle")}
        description={t("bookingCalendar.nights.noRoomsDescription")}
        action={
          <ButtonLink variant="secondary" href={`${businessPath(business.id, "assistant/knowledge")}/resources`}>
            {t("bookingCalendar.day.toPlaces")}
          </ButtonLink>
        }
      />
    );
  }

  const template = `minmax(8.5rem, 11rem) repeat(${dates.length}, minmax(3.5rem, 1fr))`;
  const container = () => scrollRef.current;
  const stays = grid.bookings.filter((booking) => booking.status !== "cancelled");
  return (
    <div className="space-y-3">
      <div
        ref={scrollRef}
        role="region"
        tabIndex={-1}
        aria-label={t("bookingCalendar.nights.label", { range: formatLocalDateRange(from, grid.date_to, locale) })}
        data-calendar-nights={from}
        className="overflow-x-auto overscroll-x-contain rounded-2xl border border-line bg-surface"
      >
        <div style={{ minWidth: `calc(8.5rem + ${dates.length} * 3.5rem)` }}>
          <div className="grid border-b border-line" style={{ gridTemplateColumns: template }}>
            <div className="sticky start-0 z-20 flex items-end border-e border-line bg-surface px-3 py-2 text-xs font-medium text-ink-subtle">
              {t("bookingCalendar.nights.room")}
            </div>
            {dates.map((date, index) => (
              <div
                key={date}
                data-night-index={index}
                className={cn(
                  "flex flex-col items-center border-e border-line px-1 py-1.5 text-xs last:border-e-0",
                  date === today ? "bg-accent-soft text-accent-ink" : "text-ink-muted",
                )}
              >
                <span className="text-[10px] tracking-wide uppercase">{formatLocalDate(date, locale, { weekday: "short" })}</span>
                <span className="font-semibold tabular-nums">{formatLocalDate(date, locale, { day: "numeric" })}</span>
              </div>
            ))}
          </div>
          {rooms.map((room) => {
            const entries = stays.flatMap((booking) => {
              const nights = booking.resource_id === room.id ? stayNights(booking, from, dates.length) : null;
              return nights ? [{ item: booking, nights }] : [];
            });
            const layout = layoutStays(entries, room.unit_count);
            const shown: ShownStay[] = layout.stays.map((laned) => ({
              laned,
              nights: entries.find((entry) => entry.item.id === laned.item.id)?.nights ?? { first: 0, count: 1, startsBefore: false, endsAfter: false },
            }));
            return (
              <NightsRow
                key={room.id}
                room={room}
                dates={dates}
                placeDays={grid.days.map((day) => day.places.find((placeDay) => placeDay.resource_id === room.id))}
                stays={shown}
                lanes={layout.lanes}
                ghost={ghostFor(room.id, gestures.preview, from, dates.length)}
                movingId={gestures.preview?.booking.id ?? null}
                template={template}
                hintId={hintId}
                onOpen={onOpen}
                onCreate={(date) => onCreate({ date, resourceId: room.id })}
                movable={gestures.movable}
                locator={(booking) => nightsLocator(container, booking, from)}
              />
            );
          })}
        </div>
      </div>
      <CalendarLegend hintId={hintId} showHint={stays.length > 0} />
      <p className="sr-only" role="status" aria-live="polite">
        {announcement}
      </p>
    </div>
  );
}

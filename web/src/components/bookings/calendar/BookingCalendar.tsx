"use client";

import { useId } from "react";

import { useLocalNow } from "@/app/b/[businessId]/bookings/_lib/useLocalNow";
import { useBusiness } from "@/components/business/BusinessContext";
import { RefreshFailed } from "@/components/insights/common";
import { addDays } from "@/components/insights/dates";
import type { BookingView } from "@/components/insights/types";
import { Alert, Card, ErrorState, LoadingRegion, Skeleton } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { firstDayOfWeek } from "@/lib/intl/localeCalendar";

import { calendarWindow } from "./_lib/calendarDates";
import { filledGrid, type CalendarView } from "./_lib/calendarTypes";
import { minuteOfTime } from "./_lib/dayLayout";
import { CalendarToolbar } from "./CalendarToolbar";
import { DayView } from "./day/DayView";
import { MoveMessageOffer } from "./MoveMessageOffer";
import { NightsView } from "./nights/NightsView";
import { useBookingGrid } from "./useBookingGrid";
import { useCalendarMove } from "./useCalendarMove";
import { WeekHeatmap } from "./week/WeekHeatmap";

/** What a new booking started on the calendar is filled in with. */
export interface CalendarDraft {
  date: string;
  time?: string;
  resourceId: string;
}

/**
 * The bookings calendar (Bookings → Day, Week, Nights) in the business
 * time zone: the toolbar's dates, then one day by place, the week's
 * heatmap or the rooms by night, loaded in one call per window
 * (GET …/bookings/grid; the week reads the load alone). The previous
 * window stays, dimmed, while the next one loads. After a move, the
 * message about the new time for the customer is offered above the grid.
 */
export function BookingCalendar({
  view,
  anchor,
  includeTest,
  onNavigate,
  onOpen,
  onCreate,
}: {
  view: CalendarView;
  anchor: string;
  includeTest: boolean;
  onNavigate: (change: { view?: CalendarView; anchor?: string; includeTest?: boolean }) => void;
  onOpen: (booking: BookingView) => void;
  onCreate: (draft: CalendarDraft) => void;
}) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const now = useLocalNow(business.timezone);
  const today = now.slice(0, 10);
  const window = calendarWindow(view, anchor, firstDayOfWeek(locale));
  const grid = useBookingGrid(window, { includeTest, withBookings: view !== "week" });
  const { move, message, dismissMessage } = useCalendarMove();
  const headingId = useId();
  const data = grid.data ? filledGrid(grid.data) : undefined;

  return (
    <section aria-labelledby={headingId} className="space-y-4">
      <CalendarToolbar
        headingId={headingId}
        view={view}
        anchor={anchor}
        window={{ from: window.from, to: addDays(window.from, window.days - 1) }}
        today={today}
        includeTest={includeTest}
        onAnchor={(date) => onNavigate({ anchor: date })}
        onIncludeTest={(include) => onNavigate({ includeTest: include })}
      />
      {grid.error && data ? <RefreshFailed error={grid.error} onRetry={grid.reload} /> : null}
      {data?.is_truncated ? <Alert tone="warning">{t("bookingCalendar.truncated")}</Alert> : null}
      <MoveMessageOffer message={message} onDismiss={dismissMessage} />
      {data === undefined ? (
        grid.error ? (
          <Card>
            <ErrorState error={grid.error} onRetry={grid.reload} />
          </Card>
        ) : (
          <LoadingRegion label={t("bookingCalendar.loading")}>
            <Skeleton className="h-[28rem] w-full rounded-2xl" />
          </LoadingRegion>
        )
      ) : (
        <div className={grid.isPlaceholder ? "animate-settle opacity-60 transition-opacity" : "animate-settle transition-opacity"} aria-busy={grid.isPlaceholder || undefined}>
          {view === "day" ? (
            <DayView
              grid={data}
              date={anchor}
              nowMinute={anchor === today ? minuteOfTime(now.slice(11, 16)) : null}
              onOpen={onOpen}
              onCreate={onCreate}
              onMove={move}
            />
          ) : view === "nights" ? (
            <NightsView grid={data} today={today} onOpen={onOpen} onCreate={onCreate} onMove={move} />
          ) : (
            <WeekHeatmap grid={data} today={today} onOpenDay={(date, next) => onNavigate({ view: next, anchor: date })} />
          )}
        </div>
      )}
    </section>
  );
}

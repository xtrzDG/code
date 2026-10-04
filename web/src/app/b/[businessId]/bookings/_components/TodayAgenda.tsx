"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconCalendar } from "@/components/icons";
import { RefreshFailed, LoadMore } from "@/components/insights/common";
import { formatLocalDate, formatLocalTime } from "@/components/insights/dates";
import type { BookingStatus, BookingView } from "@/components/insights/types";
import { Button, Card, EmptyState, ErrorState, LoadingRegion, Skeleton } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { timeOfMoment, todayAgenda } from "../_lib/todayAgenda";
import { useLocalNow } from "../_lib/useLocalNow";
import type { BookingsPage } from "../_lib/useBookingsPage";
import { AgendaCard } from "./AgendaCard";

function AgendaSkeleton() {
  return (
    <div className="space-y-3">
      {[0, 1, 2].map((index) => (
        <div key={index} className="space-y-3 rounded-2xl border border-line bg-surface p-4">
          <div className="flex gap-3">
            <Skeleton className="h-6 w-12" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-5 w-2/3" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Skeleton className="h-12 rounded-lg" />
            <Skeleton className="h-12 rounded-lg" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * The front desk's "Today" on a phone: today's arrivals by time with a
 * "now" line, the day's tally, and on each card large "Arrived" and
 * "No-show" buttons that wait for the start time. Marking takes one tap;
 * the toast's Undo takes it back.
 */
export function TodayAgenda({ page }: { page: BookingsPage }) {
  const { t, tp, locale } = useI18n();
  const { business } = useBusiness();
  const localNow = useLocalNow(business.timezone);
  const { agenda: bookings, isStay, setDialog, runStatus, isChangingStatus } = page;
  const items = bookings.items;

  if (items === undefined) {
    return bookings.error ? (
      <Card>
        <ErrorState error={bookings.error} onRetry={bookings.reload} />
      </Card>
    ) : (
      <LoadingRegion label={t("bookings.today.loading")}>
        <AgendaSkeleton />
      </LoadingRegion>
    );
  }

  const { entries, nowIndex, counts } = todayAgenda(items, localNow);
  const mark = (booking: BookingView, status: Extract<BookingStatus, "completed" | "no_show">) => {
    const name = booking.contact_name ?? t("insights.unknownCustomer");
    void runStatus(booking, status, t(status === "completed" ? "bookings.today.markedArrived" : "bookings.today.markedNoShow", { name }));
  };
  const tally = [
    t("bookings.today.toCome", { count: counts.toCome }),
    t("bookings.today.arrivedCount", { count: counts.arrived }),
    t("bookings.today.missedCount", { count: counts.missed }),
    ...(counts.cancelled > 0 ? [tp("bookings.today.cancelled", counts.cancelled)] : []),
  ];

  return (
    <section aria-labelledby="bookings-today" className="space-y-3">
      <header className="space-y-0.5">
        <h2 id="bookings-today" className="text-base font-semibold text-ink">
          {t("bookings.today.heading", {
            date: formatLocalDate(page.today, locale, { weekday: "long", day: "numeric", month: "long" }),
          })}
        </h2>
        <p className="text-sm text-ink-muted tabular-nums">{tally.join(" · ")}</p>
      </header>
      {bookings.error ? <RefreshFailed error={bookings.error} onRetry={bookings.reload} /> : null}

      {entries.length === 0 ? (
        <Card>
          <EmptyState
            icon={<IconCalendar className="size-6" />}
            title={t("bookings.today.emptyTitle")}
            description={t("bookings.today.emptyDescription")}
            action={
              <Button variant="secondary" onClick={() => page.setPhoneView("all")}>
                {t("bookings.today.showAll")}
              </Button>
            }
          />
        </Card>
      ) : (
        <ol aria-label={t("bookings.today.label")} className="space-y-3">
          {entries.map((entry, index) => (
            <li key={entry.booking.id} className="space-y-3">
              {index === nowIndex ? (
                <p className="flex items-center gap-2 text-xs font-semibold text-accent">
                  <span aria-hidden className="h-px flex-1 bg-accent/40" />
                  {t("bookings.today.now", { time: formatLocalTime(timeOfMoment(localNow), locale) })}
                  <span aria-hidden className="h-px flex-1 bg-accent/40" />
                </p>
              ) : null}
              <AgendaCard
                entry={entry}
                isStay={isStay(entry.booking)}
                isBusy={isChangingStatus}
                onOpen={(booking) => setDialog({ kind: "details", booking })}
                onMark={mark}
              />
            </li>
          ))}
        </ol>
      )}
      <LoadMore hasMore={bookings.hasMore} isLoading={bookings.isLoadingMore} error={bookings.moreError} onMore={bookings.loadMore} />
    </section>
  );
}

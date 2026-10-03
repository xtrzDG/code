"use client";

import { IconCalendar, IconPlus } from "@/components/icons";
import { RefreshFailed } from "@/components/insights/common";
import { useBusiness } from "@/components/business/BusinessContext";
import { Button, Card, EmptyState, ErrorState, LoadingRegion, PageHeader } from "@/components/ui";
import { LiveStatus } from "@/components/shell/LiveStatus";
import { useI18n } from "@/i18n/client";
import { timeZoneLabel } from "@/lib/timeZones";

import { BookingDialogs } from "./_components/BookingDialogs";
import { BookingFiltersBar } from "./_components/BookingFiltersBar";
import { BookingDays } from "./_components/BookingList";
import { BookingDaysSkeleton } from "./_components/BookingsSkeleton";
import type { BookingFilters } from "./_lib/bookingFilters";
import { useBookingsPage } from "./_lib/useBookingsPage";

/**
 * Bookings in the business time zone (concept /bookings): filters by dates,
 * status and place (applied and paged by the API), a booking added by hand
 * with free slots, status changes, edits (party, place, notes, name),
 * moving and cancelling with the text for the customer.
 */
export function BookingsScreen({ initialFilters }: { initialFilters: BookingFilters }) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const page = useBookingsPage(initialFilters);
  const { filters, setFilters, rangeValid, bookings, resources, setDialog, isStay } = page;
  const items = bookings.items ?? [];

  return (
    <>
      <PageHeader
        title={t("nav.bookings")}
        description={t("pages.bookings.description")}
        actions={
          <>
            <LiveStatus updatedAt={bookings.updatedAt} isFetching={bookings.isFetching && bookings.items !== undefined} />
            <Button leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => setDialog({ kind: "create" })}>
              {t("bookings.newBooking")}
            </Button>
          </>
        }
      />

      <div className="space-y-5">
        <BookingFiltersBar
          filters={filters}
          resources={resources}
          rangeError={rangeValid ? null : t("bookings.rangeInvalid")}
          onChange={setFilters}
        />
        <p className="text-xs text-ink-subtle">{t("bookings.timeZoneNote", { timezone: timeZoneLabel(business.timezone, locale) })}</p>
        {bookings.error && bookings.items ? <RefreshFailed error={bookings.error} onRetry={bookings.reload} /> : null}

        {!rangeValid ? null : bookings.items === undefined ? (
          bookings.error ? (
            <Card>
              <ErrorState error={bookings.error} onRetry={bookings.reload} />
            </Card>
          ) : (
            <LoadingRegion label={t("bookings.loading")}>
              <BookingDaysSkeleton />
            </LoadingRegion>
          )
        ) : items.length === 0 && !bookings.isPlaceholder ? (
          <Card>
            <EmptyState
              icon={<IconCalendar className="size-6" />}
              title={t("bookings.emptyTitle")}
              description={t("bookings.emptyDescription")}
              action={
                <Button variant="secondary" leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => setDialog({ kind: "create" })}>
                  {t("bookings.newBooking")}
                </Button>
              }
            />
          </Card>
        ) : (
          <div
            className={bookings.isPlaceholder ? "animate-settle opacity-60 transition-opacity" : "animate-settle transition-opacity"}
            aria-busy={bookings.isPlaceholder || undefined}
          >
            <BookingDays
              bookings={items}
              newestFirst={filters.range === "past"}
              isStay={isStay}
              onOpen={(booking) => setDialog({ kind: "details", booking })}
              paging={{
                hasMore: bookings.hasMore,
                isLoading: bookings.isLoadingMore,
                error: bookings.moreError,
                onMore: bookings.loadMore,
              }}
            />
          </div>
        )}
      </div>
      <BookingDialogs page={page} />
    </>
  );
}

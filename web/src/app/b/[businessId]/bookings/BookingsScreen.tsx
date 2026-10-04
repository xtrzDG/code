"use client";

import { IconCalendar, IconPlus } from "@/components/icons";
import { RefreshFailed } from "@/components/insights/common";
import { SegmentedControl } from "@/components/insights/SegmentedControl";
import { useBusiness } from "@/components/business/BusinessContext";
import { ExportCsvButton } from "@/components/exports/ExportCsvButton";
import { Button, Card, EmptyState, ErrorState, LoadingRegion, PageHeader } from "@/components/ui";
import { LiveStatus } from "@/components/shell/LiveStatus";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { timeZoneLabel } from "@/lib/timeZones";

import { BookingDialogs } from "./_components/BookingDialogs";
import { BookingFiltersBar } from "./_components/BookingFiltersBar";
import { BookingDays } from "./_components/BookingList";
import { BookingDaysSkeleton } from "./_components/BookingsSkeleton";
import { TodayAgenda } from "./_components/TodayAgenda";
import { bookingApiQuery, type BookingFilters, type PhoneBookingsView } from "./_lib/bookingFilters";
import { useBookingsPage } from "./_lib/useBookingsPage";

/**
 * Bookings in the business time zone (concept /bookings): filters by dates,
 * status and place (applied and paged by the API), a booking added by hand
 * with free slots, status changes with Undo, edits (party, place, notes,
 * name), moving and cancelling with the text for the customer. A phone
 * opens on today's agenda for the front desk ("All bookings" is the list).
 */
export function BookingsScreen({ initialFilters }: { initialFilters: BookingFilters }) {
  const { t, locale } = useI18n();
  const { business, isOwner } = useBusiness();
  const page = useBookingsPage(initialFilters);
  const { filters, setFilters, rangeValid, bookings, agenda, resources, setDialog, isStay } = page;
  const items = bookings.items ?? [];
  const isToday = filters.phoneView === "today";
  const openCreate = () => setDialog({ kind: "create" });
  // The live status of what is on screen: the agenda on a phone's "Today", else the list.
  const shown = page.isCompact && isToday ? agenda : bookings;

  return (
    <>
      <PageHeader
        title={t("nav.bookings")}
        description={t("pages.bookings.description")}
        status={<LiveStatus updatedAt={shown.updatedAt} isFetching={shown.isFetching && shown.items !== undefined} />}
        actions={
          isOwner ? (
            <ExportCsvButton
              table="bookings"
              query={bookingApiQuery(filters, page.range)}
              hint={t("dataExports.csv.bookingsHint")}
              disabled={!rangeValid}
            />
          ) : undefined
        }
        primaryAction={{ label: t("bookings.newBooking"), icon: IconPlus, onClick: openCreate, opensDialog: true }}
      />

      <SegmentedControl<PhoneBookingsView>
        label={t("bookings.views.label")}
        value={filters.phoneView}
        onChange={page.setPhoneView}
        options={[
          { value: "today", label: t("bookings.views.today") },
          { value: "all", label: t("bookings.views.all") },
        ]}
        className="mb-4 lg:hidden"
      />

      <div className={cn("lg:hidden", !isToday && "hidden")}>
        <TodayAgenda page={page} />
      </div>

      <div className={cn("space-y-5", isToday && "max-lg:hidden")}>
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
                <Button variant="secondary" leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={openCreate}>
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

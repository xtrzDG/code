"use client";

import Link from "next/link";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconChevronRight } from "@/components/icons";
import { BookingStatusBadge, ChannelBadge, TestBadge } from "@/components/insights/Badges";
import { CustomerName, DetailRow, LoadMore, PhoneLink } from "@/components/insights/common";
import { formatLocalDate, formatLocalTime } from "@/components/insights/dates";
import { useToday } from "@/components/insights/useToday";
import { CHANNEL_LABELS } from "@/components/insights/labels";
import type { BookingView } from "@/components/insights/types";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";
import { businessPath } from "@/lib/navigation";

import { groupBookingsByDate, nightsOf, reminderState } from "./bookingModel";

/** "20:00–22:00" for slots, "3 nights · until Oct 6" for stays. */
export function useBookingWhen() {
  const { t, tp, locale } = useI18n();
  return {
    time: (booking: BookingView, isStay: boolean): { main: string; sub: string | null } => {
      if (isStay) {
        return {
          main: tp("bookings.nights", nightsOf(booking)),
          sub: t("bookings.untilDate", {
            date: formatLocalDate(booking.end_date, locale, { day: "numeric", month: "short" }),
          }),
        };
      }
      return {
        main: booking.time ? formatLocalTime(booking.time, locale) : "–",
        sub: booking.end_time ? formatLocalTime(booking.end_time, locale) : null,
      };
    },
    full: (booking: BookingView, isStay: boolean): string => {
      const date = formatLocalDate(booking.date, locale, { weekday: "long", day: "numeric", month: "long", year: "numeric" });
      if (isStay) {
        return `${date}, ${tp("bookings.nights", nightsOf(booking))}`;
      }
      const times = [booking.time, booking.end_time].filter(Boolean).map((time) => formatLocalTime(time ?? "", locale));
      return times.length > 0 ? `${date}, ${times.join("–")}` : date;
    },
  };
}

/** Loaded bookings grouped by local day; the API pages them ("show more"). */
export function BookingDays({
  bookings,
  newestFirst,
  isStay,
  onOpen,
  paging,
}: {
  bookings: readonly BookingView[];
  newestFirst: boolean;
  isStay: (booking: BookingView) => boolean;
  onOpen: (booking: BookingView) => void;
  paging: { hasMore: boolean; isLoading: boolean; error: unknown; onMore: () => void };
}) {
  const { tp, locale } = useI18n();
  const days = groupBookingsByDate(bookings, { newestFirst });
  return (
    <div className="space-y-4">
      {days.map((day) => {
        const headingId = `bookings-day-${day.date}`;
        return (
          <section
            key={day.date}
            aria-labelledby={headingId}
            className="overflow-hidden rounded-2xl border border-line bg-surface shadow-sm"
          >
            <header className="flex items-baseline justify-between gap-3 border-b border-line bg-surface-muted/60 px-4 py-2.5 sm:px-5">
              <h2 id={headingId} className="text-sm font-semibold text-ink">
                {formatLocalDate(day.date, locale, { weekday: "long", day: "numeric", month: "long" })}
              </h2>
              <span className="text-xs text-ink-muted">{tp("bookings.count", day.bookings.length)}</span>
            </header>
            <ul className="divide-y divide-line">
              {day.bookings.map((booking) => (
                <BookingRow key={booking.id} booking={booking} isStay={isStay(booking)} onOpen={() => onOpen(booking)} />
              ))}
            </ul>
          </section>
        );
      })}
      <LoadMore hasMore={paging.hasMore} isLoading={paging.isLoading} error={paging.error} onMore={paging.onMore} />
    </div>
  );
}

function BookingRow({ booking, isStay, onOpen }: { booking: BookingView; isStay: boolean; onOpen: () => void }) {
  const { t, tp } = useI18n();
  const when = useBookingWhen().time(booking, isStay);
  const isInactive = booking.status === "cancelled" || booking.status === "no_show";

  return (
    <li>
      <button
        type="button"
        onClick={onOpen}
        className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-muted focus-visible:-outline-offset-2 sm:gap-4 sm:px-5"
      >
        <span className="w-16 shrink-0 tabular-nums sm:w-20">
          <span className={isInactive ? "block font-semibold text-ink-subtle line-through" : "block font-semibold text-ink"}>
            {when.main}
          </span>
          {when.sub ? <span className="block text-xs text-ink-subtle">{when.sub}</span> : null}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="font-medium text-ink">
              <CustomerName name={booking.contact_name} />
            </span>
            <BookingStatusBadge status={booking.status} />
            {booking.is_sandbox ? <TestBadge /> : null}
          </span>
          <span className="mt-0.5 block text-sm text-ink-muted">
            {[tp("bookings.guests", booking.party_size), booking.resource_name, t(CHANNEL_LABELS[booking.source_channel])].join(
              " · ",
            )}
            {booking.contact_phone_number ? (
              <>
                {" · "}
                <span dir="ltr" className="tabular-nums">
                  {booking.contact_phone_number}
                </span>
              </>
            ) : null}
          </span>
          {booking.notes ? (
            <span dir="auto" className="mt-0.5 line-clamp-1 text-sm text-ink-subtle">
              {booking.notes}
            </span>
          ) : null}
        </span>
        <IconChevronRight className="mt-1 size-4 shrink-0 text-ink-subtle" aria-hidden />
      </button>
    </li>
  );
}

/** Everything about one booking, as a definition list. */
export function BookingDetails({ booking, isStay }: { booking: BookingView; isStay: boolean }) {
  const { t, tp, locale } = useI18n();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const today = useToday(business.timezone);
  const when = useBookingWhen();
  const reminder = reminderState(booking, today);
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <BookingStatusBadge status={booking.status} />
        {booking.is_sandbox ? <TestBadge /> : null}
      </div>
      <dl className="divide-y divide-line">
        <DetailRow label={t("bookings.details.when")}>{when.full(booking, isStay)}</DetailRow>
        <DetailRow label={t("bookings.details.place")}>
          <span dir="auto">{booking.resource_name}</span>
        </DetailRow>
        <DetailRow label={t("bookings.details.party")}>{tp("bookings.guests", booking.party_size)}</DetailRow>
        <DetailRow label={t("bookings.details.phone")}>
          {booking.contact_phone_number ? <PhoneLink phone={booking.contact_phone_number} /> : "–"}
        </DetailRow>
        <DetailRow label={t("bookings.details.source")}>
          <ChannelBadge channel={booking.source_channel} />
        </DetailRow>
        {booking.language ? (
          <DetailRow label={t("bookings.details.language")}>{languageName(booking.language, locale)}</DetailRow>
        ) : null}
        <DetailRow label={t("bookings.details.reminder")}>
          {reminder === "sent" && booking.reminder_sent_at
            ? t("bookings.reminder.sent", { date: format.dateTime(booking.reminder_sent_at) })
            : t(reminder === "pending" ? "bookings.reminder.pending" : "bookings.reminder.none")}
        </DetailRow>
        <DetailRow label={t("bookings.details.created")}>{format.dateTime(booking.created_at)}</DetailRow>
        {booking.notes ? (
          <DetailRow label={t("bookings.details.notes")}>
            <span dir="auto" className="whitespace-pre-wrap">
              {booking.notes}
            </span>
          </DetailRow>
        ) : null}
      </dl>
      {booking.conversation_id ? (
        <Link
          href={`${businessPath(business.id, "conversations")}/${encodeURIComponent(booking.conversation_id)}`}
          className="inline-flex text-sm font-medium text-accent hover:underline"
        >
          {t("insights.openConversation")}
        </Link>
      ) : null}
    </div>
  );
}

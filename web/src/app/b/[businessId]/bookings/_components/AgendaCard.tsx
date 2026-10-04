"use client";

import { useId } from "react";

import { IconCheck, IconPhone, IconX } from "@/components/icons";
import { BookingStatusBadge, TestBadge } from "@/components/insights/Badges";
import { CustomerName } from "@/components/insights/common";
import { usePartyWording } from "@/components/insights/usePartyWording";
import type { BookingView } from "@/components/insights/types";
import { Badge, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatPhone } from "@/lib/phone";

import type { AgendaEntry } from "../_lib/todayAgenda";
import { useBookingWhen } from "./BookingList";

/**
 * One arrival of today's agenda: the time and who comes, what for and
 * where, then two large buttons, "Arrived" and "No-show", which wait for
 * the start time (a hint says from when). A marked booking folds to its
 * result. The card itself opens the booking; the phone icon calls.
 */
export function AgendaCard({
  entry,
  isStay,
  isBusy,
  onOpen,
  onMark,
}: {
  entry: AgendaEntry;
  isStay: boolean;
  isBusy: boolean;
  onOpen: (booking: BookingView) => void;
  onMark: (booking: BookingView, status: "completed" | "no_show") => void;
}) {
  const { t } = useI18n();
  const party = usePartyWording();
  const hintId = useId();
  const { booking, isActive, canMark } = entry;
  const when = useBookingWhen().time(booking, isStay);
  const name = booking.contact_name ?? t("insights.unknownCustomer");
  const details = [party.count(booking.party_size, booking.resource_id), booking.resource_name, booking.service_title]
    .filter(Boolean)
    .join(" · ");

  return (
    <article
      data-booking-card={booking.id}
      className={cn(
        "overflow-hidden rounded-2xl border bg-surface shadow-sm transition-colors",
        isActive ? "border-line" : "border-line/60 bg-surface/60",
      )}
    >
      <div className="flex items-stretch">
        <button
          type="button"
          onClick={() => onOpen(booking)}
          aria-label={t("bookings.today.open", { name })}
          className="flex min-w-0 flex-1 cursor-pointer items-start gap-3 px-4 py-3.5 text-start transition-colors hover:bg-surface-muted/60 focus-visible:-outline-offset-2"
        >
          <span className="w-14 shrink-0 tabular-nums">
            <span className={cn("block text-lg leading-6 font-semibold", isActive ? "text-ink" : "text-ink-subtle")}>{when.main}</span>
            {when.sub ? <span className="block text-xs text-ink-subtle">{when.sub}</span> : null}
          </span>
          <span className="min-w-0 flex-1">
            <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span className={cn("text-base font-semibold", isActive ? "text-ink" : "text-ink-muted")}>
                <CustomerName name={booking.contact_name} />
              </span>
              {booking.status === "pending" ? <BookingStatusBadge status={booking.status} /> : null}
              {booking.is_sandbox ? <TestBadge /> : null}
            </span>
            <span dir="auto" className="mt-0.5 block text-sm text-ink-muted">
              {details}
            </span>
            {booking.notes ? (
              <span dir="auto" className="mt-0.5 line-clamp-1 block text-sm text-ink-subtle">
                {booking.notes}
              </span>
            ) : null}
          </span>
        </button>
        {booking.contact_phone_number ? (
          <a
            href={`tel:${booking.contact_phone_number}`}
            aria-label={t("bookings.today.call", { name: `${name} (${formatPhone(booking.contact_phone_number)})` })}
            className="motion-press m-2 ms-0 flex size-11 shrink-0 items-center justify-center self-start rounded-full text-accent hover:bg-accent-soft focus-visible:outline-2 focus-visible:outline-focus"
          >
            <IconPhone className="size-5" aria-hidden />
          </a>
        ) : null}
      </div>

      {isActive ? (
        <div className="border-t border-line px-3 pt-3 pb-3">
          <div className="grid grid-cols-2 gap-2" role="group" aria-label={name}>
            <Button
              className="h-12 text-base"
              leadingIcon={<IconCheck className="size-5" aria-hidden />}
              disabled={!canMark || isBusy}
              aria-describedby={canMark ? undefined : hintId}
              onClick={() => onMark(booking, "completed")}
            >
              {t("bookings.today.arrived")}
            </Button>
            <Button
              variant="secondary"
              className="h-12 text-base"
              leadingIcon={<IconX className="size-5" aria-hidden />}
              disabled={!canMark || isBusy}
              aria-describedby={canMark ? undefined : hintId}
              onClick={() => onMark(booking, "no_show")}
            >
              {t("bookings.today.noShow")}
            </Button>
          </div>
          {canMark ? null : (
            <p id={hintId} className="mt-2 text-center text-xs text-ink-subtle">
              {t("bookings.today.availableAt", { time: when.main })}
            </p>
          )}
        </div>
      ) : (
        <div className="flex items-center gap-2 border-t border-line/60 px-4 py-2.5">
          <Badge
            tone={booking.status === "completed" ? "success" : "danger"}
            icon={booking.status === "completed" ? <IconCheck className="size-3.5" aria-hidden /> : <IconX className="size-3.5" aria-hidden />}
          >
            {t(booking.status === "completed" ? "bookings.today.arrived" : "bookings.today.noShow")}
          </Badge>
        </div>
      )}
    </article>
  );
}

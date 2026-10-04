"use client";

import type { BookingView } from "@/components/insights/types";
import { Button, OverflowMenu, type MenuAction } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import { bookingActionLayout, bookingActions, hasStarted, type BookingActionKey } from "../_lib/bookingList";
import { useLocalNow } from "../_lib/useLocalNow";
import type { BookingsPage } from "../_lib/useBookingsPage";

const LABELS: Record<BookingActionKey | "edit", MessageKey> = {
  confirm: "bookings.actions.confirm",
  complete: "bookings.actions.complete",
  noShow: "bookings.actions.noShow",
  reschedule: "bookings.actions.reschedule",
  cancel: "bookings.actions.cancel",
  edit: "bookings.actions.edit",
};

/**
 * The buttons under a booking's details: one main action (confirm a
 * request; once the booking has started, mark it completed; otherwise
 * edit) and the rest under "More", cancelling last. "Completed" and
 * "No-show" wait for the start time.
 */
export function BookingDetailActions({ booking, page }: { booking: BookingView; page: BookingsPage }) {
  const { t } = useI18n();
  const { setDialog, close, openCancel } = page;
  const localNow = useLocalNow(booking.timezone);
  const actions = bookingActions(booking.status, hasStarted(booking, localNow));
  const { primary, more } = bookingActionLayout(actions);

  const run: Record<BookingActionKey | "edit", () => void> = {
    confirm: () => void page.runStatus(booking, "confirmed"),
    complete: () => void page.runStatus(booking, "completed"),
    noShow: () => setDialog({ kind: "noShow", booking }),
    reschedule: () => setDialog({ kind: "reschedule", booking }),
    cancel: () => openCancel(booking),
    edit: () => setDialog({ kind: "edit", booking }),
  };
  const menu: MenuAction[] = more.map((key) => ({
    key,
    label: t(LABELS[key]),
    onSelect: run[key],
    tone: key === "cancel" ? "danger" : undefined,
  }));
  const isFinished = !Object.values(actions).some(Boolean);

  return (
    <div className="flex w-full flex-wrap items-center justify-end gap-2" role="group" aria-label={t("bookings.actions.label")}>
      <OverflowMenu label={t("bookings.actions.more")} actions={menu} />
      {isFinished ? (
        <>
          <Button variant="secondary" size="sm" className="whitespace-nowrap" onClick={run.edit}>
            {t(LABELS.edit)}
          </Button>
          <Button variant="secondary" size="sm" className="whitespace-nowrap" onClick={close}>
            {t("common.close")}
          </Button>
        </>
      ) : (
        <Button size="sm" className="whitespace-nowrap" variant={primary === "edit" ? "secondary" : "primary"} onClick={run[primary]}>
          {t(LABELS[primary])}
        </Button>
      )}
    </div>
  );
}

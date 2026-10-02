"use client";

import type { BookingView } from "@/components/insights/types";
import { Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { bookingActions } from "../_lib/bookingList";
import type { BookingsPage } from "../_lib/useBookingsPage";

/** The buttons under a booking's details: what its status allows, edit and close. */
export function BookingDetailActions({ booking, page }: { booking: BookingView; page: BookingsPage }) {
  const { t } = useI18n();
  const { setDialog, close, openCancel } = page;
  const actions = bookingActions(booking.status);
  const editButton = (
    <Button variant="secondary" size="sm" onClick={() => setDialog({ kind: "edit", booking })}>
      {t("bookings.actions.edit")}
    </Button>
  );
  if (!Object.values(actions).some(Boolean)) {
    return (
      <div className="flex w-full flex-wrap justify-end gap-2">
        {editButton}
        <Button variant="secondary" size="sm" onClick={close}>
          {t("common.close")}
        </Button>
      </div>
    );
  }
  return (
    <div className="flex w-full flex-wrap justify-end gap-2" role="group" aria-label={t("bookings.actions.label")}>
      {actions.cancel ? (
        <Button variant="ghost" size="sm" className="text-danger! sm:mr-auto" onClick={() => openCancel(booking)}>
          {t("bookings.actions.cancel")}
        </Button>
      ) : null}
      {editButton}
      {actions.noShow ? (
        <Button variant="secondary" size="sm" onClick={() => setDialog({ kind: "noShow", booking })}>
          {t("bookings.actions.noShow")}
        </Button>
      ) : null}
      {actions.reschedule ? (
        <Button variant="secondary" size="sm" onClick={() => setDialog({ kind: "reschedule", booking })}>
          {t("bookings.actions.reschedule")}
        </Button>
      ) : null}
      {actions.complete ? (
        <Button variant="secondary" size="sm" isLoading={page.isChangingStatus} onClick={() => void page.runStatus(booking, "completed")}>
          {t("bookings.actions.complete")}
        </Button>
      ) : null}
      {actions.confirm ? (
        <Button size="sm" isLoading={page.isChangingStatus} onClick={() => void page.runStatus(booking, "confirmed")}>
          {t("bookings.actions.confirm")}
        </Button>
      ) : null}
    </div>
  );
}

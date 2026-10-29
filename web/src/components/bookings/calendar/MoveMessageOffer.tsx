"use client";

import { useState } from "react";

import { CustomerMessageModal } from "@/components/insights/CustomerMessageModal";
import { Alert, Button, UserSentence } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import type { MoveMessage } from "./useCalendarMove";

/**
 * After a booking was moved on the calendar (drag or keys), the offer to
 * tell the customer the new time: the same message, title and copy button
 * the list's reschedule form shows (CustomerMessageModal), opened from here
 * so moving several bookings in a row is not interrupted. Done in the
 * message, or Close here, puts the offer away.
 */
export function MoveMessageOffer({ message, onDismiss }: { message: MoveMessage | null; onDismiss: () => void }) {
  const { t } = useI18n();
  const [isOpen, setIsOpen] = useState(false);
  if (message === null) {
    return null;
  }
  const name = message.booking.contact_name;

  return (
    <>
      <Alert
        className="animate-settle"
        title={
          name ? (
            <UserSentence text={t("bookingCalendar.move.tell.title")} values={{ name }} />
          ) : (
            t("bookingCalendar.move.tell.titleAnonymous")
          )
        }
        action={
          <>
            <Button size="sm" onClick={() => setIsOpen(true)}>
              {t("bookingCalendar.move.tell.show")}
            </Button>
            <Button size="sm" variant="ghost" onClick={onDismiss}>
              {t("common.close")}
            </Button>
          </>
        }
      >
        {t("bookingCalendar.move.tell.hint")}
      </Alert>
      <CustomerMessageModal
        open={isOpen}
        title={t("bookings.rescheduled")}
        text={message.text}
        onClose={() => {
          setIsOpen(false);
          onDismiss();
        }}
      />
    </>
  );
}

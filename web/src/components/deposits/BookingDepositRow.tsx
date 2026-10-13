"use client";

import type { BookingView } from "@/components/insights/types";

import { DepositPayment } from "./DepositPayment";
import { bookingAfterPaid, type BookingDepositView } from "./depositModel";

/**
 * A booking's deposit in its details, with "Paid": a paid booking held for
 * its deposit is confirmed.
 */
export function BookingDepositRow({
  booking,
  deposit,
  onPaid,
}: {
  booking: BookingView;
  deposit: BookingDepositView;
  onPaid: (booking: BookingView) => void;
}) {
  return (
    <DepositPayment
      deposit={deposit}
      heldUntilKey="deposits.booking.heldUntil"
      confirmKey="deposits.booking.confirmDescription"
      onPaid={() => onPaid(bookingAfterPaid(booking))}
    />
  );
}

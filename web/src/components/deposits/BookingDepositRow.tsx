"use client";

import { useState } from "react";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import type { BookingView } from "@/components/insights/types";
import { Alert, Button, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { DepositBadge } from "./DepositBadge";
import { bookingAfterPaid, canMarkPaid, type BookingDepositView } from "./depositModel";
import { useDepositRequest, useMarkDepositPaid } from "./useDeposits";

/**
 * A booking's deposit in its details: the amount and its state, until when
 * the place is held, the reference and page the customer pays with, and
 * "Paid" for staff who see the money in their merchant account (asked once
 * more in place, never by the assistant). A paid booking held for its
 * deposit is confirmed.
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
  const { t } = useI18n();
  const toast = useToast();
  const format = useBusinessFormat();
  const request = useDepositRequest(deposit.request_id);
  const markPaid = useMarkDepositPaid();
  const [isConfirming, setConfirming] = useState(false);
  const amount = format.money(deposit.amount_minor, deposit.currency_code);
  const reference = request.data?.reference ?? null;

  const confirm = async () => {
    const result = await markPaid.run(deposit.request_id);
    setConfirming(false);
    if (result.ok) {
      request.setData(result.data);
      toast.success(t("deposits.booking.marked"));
      onPaid(bookingAfterPaid(booking));
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-ink tabular-nums">{amount}</span>
        <DepositBadge status={deposit.status} />
      </div>
      {deposit.status === "awaiting" && deposit.hold_expires_at ? (
        <p className="text-ink-muted">{t("deposits.booking.heldUntil", { time: format.dateTime(deposit.hold_expires_at) })}</p>
      ) : null}
      {reference ? (
        <p className="text-ink-muted">
          {t("deposits.booking.reference", { reference })}
          {request.data?.payment_link_label ? (
            <>
              {" · "}
              <span dir="auto" data-user-content>
                {request.data.payment_link_label}
              </span>
            </>
          ) : null}
        </p>
      ) : null}
      {deposit.status === "refund_due" ? <Alert tone="warning">{t("deposits.booking.refundDue")}</Alert> : null}
      {canMarkPaid(deposit) && !isConfirming ? (
        <Button size="sm" variant="secondary" onClick={() => setConfirming(true)}>
          {t("deposits.booking.markPaid")}
        </Button>
      ) : null}
      {canMarkPaid(deposit) && isConfirming ? (
        <div role="group" aria-label={t("deposits.booking.confirmTitle")} className="space-y-2 rounded-xl bg-surface-muted p-3">
          <p className="font-medium text-ink">{t("deposits.booking.confirmTitle")}</p>
          <p className="text-ink-muted">
            {t("deposits.booking.confirmDescription", { amount, reference: reference ?? "–" })}
          </p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" autoFocus isLoading={markPaid.isPending} onClick={() => void confirm()}>
              {t("deposits.booking.confirm")}
            </Button>
            <Button size="sm" variant="secondary" disabled={markPaid.isPending} onClick={() => setConfirming(false)}>
              {t("common.cancel")}
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

"use client";

import type { Schema } from "@/api/types";
import { Badge, Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { useClientFormat } from "../../_lib/useClientFormat";
import { PAYMENT_STATUS_LABELS } from "../labels";

/** The client's payments with their amount, status and why one failed. */
export function PaymentsCard({ payments, timeZone }: { payments: Schema<"AdminPaymentView">[]; timeZone: string }) {
  const { t } = useI18n();
  const { dateTime, money } = useClientFormat(timeZone);
  return (
    <Card title={t("admin.detail.paymentsTitle")} padded={payments.length === 0}>
      {payments.length === 0 ? (
        <p className="text-sm text-ink-muted">{t("admin.detail.noPayments")}</p>
      ) : (
        <ul className="divide-y divide-line">
          {payments.map((payment) => (
            <li key={payment.id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 sm:px-6">
              <div className="text-sm">
                <p className="font-medium text-ink">{dateTime(payment.created_at)}</p>
                {payment.failure_reason ? (
                  <p className="text-xs text-danger" dir="auto">
                    {payment.failure_reason}
                  </p>
                ) : null}
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span className="font-medium">{money(payment.amount.amount_minor, payment.amount.currency_code)}</span>
                <Badge
                  tone={
                    payment.status === "approved"
                      ? "success"
                      : payment.status === "declined"
                        ? "danger"
                        : payment.status === "processing" || payment.status === "created"
                          ? "info"
                          : "neutral"
                  }
                >
                  {t(PAYMENT_STATUS_LABELS[payment.status])}
                </Badge>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { Alert } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { PAYMENT_RETRY_ATTEMPTS, retryStatusText, type PaymentRetryView } from "../_lib/paymentMethod";

/**
 * Where the retries of a declined automatic payment stand: the last try
 * and how it went, then the next one, or that none is left and from when
 * the assistant only takes requests.
 */
export function PaymentRetryStatus({ retry }: { retry: PaymentRetryView }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const isLast = !retry.next_retry_at;

  return (
    <Alert tone={isLast ? "danger" : "warning"} title={t("billingCard.retry.title")}>
      <p>{t(retryStatusText(retry), { attempt: String(retry.last_attempt ?? 0), total: String(PAYMENT_RETRY_ATTEMPTS) })}</p>
      {retry.next_retry_at ? (
        <p className="mt-1">{t("billingCard.retry.next", { date: format.dateTime(retry.next_retry_at) })}</p>
      ) : retry.grace_until ? (
        <p className="mt-1">{t("billingCard.retry.noMore", { date: format.date(retry.grace_until) })}</p>
      ) : null}
    </Alert>
  );
}

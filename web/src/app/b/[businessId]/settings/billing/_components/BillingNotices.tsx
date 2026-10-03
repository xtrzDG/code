"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { Alert, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/lib/format";

import { quotedMoneyText, type BillingNotice, type BillingOverview } from "../_lib/billing";

/** The alerts above the billing page (grace period, trial, unpaid invoices, package use). */
export function BillingNotices({
  notices,
  overview,
  canPay,
  isPaying,
  onPay,
}: {
  notices: readonly BillingNotice[];
  overview: BillingOverview;
  canPay: boolean;
  isPaying: boolean;
  onPay: () => void;
}) {
  const { t, tp, locale } = useI18n();
  const format = useBusinessFormat();
  if (notices.length === 0) {
    return null;
  }
  const percent = (value: number) =>
    formatNumber(value / 100, locale, { style: "percent", maximumFractionDigits: 0 });
  const overagePrice = overview.usage ? quotedMoneyText(overview.usage.overage_price_per_minute, format.money) : "";
  const payAction = canPay ? (
    <div className="mt-3">
      <Button size="sm" onClick={onPay} isLoading={isPaying}>
        {t("billing.pay")}
      </Button>
    </div>
  ) : null;

  return (
    <div className="space-y-3">
      {notices.map((notice) => {
        switch (notice.kind) {
          case "leadsOnly":
            return (
              <Alert key="leadsOnly" tone="danger" title={t("billing.notices.leadsOnlyTitle")}>
                {t("billing.notices.leadsOnly")}
                {payAction}
              </Alert>
            );
          case "incomplete":
            return (
              <Alert key="incomplete" tone="warning" title={t("billing.subscribe.incompleteTitle")}>
                {t("billing.subscribe.incomplete")}
                {payAction}
              </Alert>
            );
          case "pastDue":
            return (
              <Alert key="pastDue" tone="danger" title={t("billing.notices.pastDueTitle")}>
                {notice.graceUntil
                  ? t("billing.notices.pastDue", { date: format.date(notice.graceUntil) })
                  : t("billing.notices.pastDueNoDate")}
                {payAction}
              </Alert>
            );
          case "cancelled":
            return (
              <Alert key="cancelled" tone="warning" title={t("billing.notices.cancelledTitle")}>
                {t("billing.notices.cancelled", { date: format.date(notice.until) })}
                {payAction}
              </Alert>
            );
          case "unpaid":
            return (
              <Alert key="unpaid" tone="warning" title={tp("billing.notices.unpaidTitle", notice.count)}>
                {t("billing.notices.unpaid")}
                {payAction}
              </Alert>
            );
          case "trial":
            return (
              <Alert key="trial" tone="info" title={tp("billing.notices.trialTitle", notice.daysLeft)}>
                {t("billing.notices.trial", { date: format.date(notice.endsAt) })}
                {payAction}
              </Alert>
            );
          case "usage": {
            const text =
              notice.unit === "voice"
                ? t(notice.isExceeded ? "billing.notices.usageVoiceExceeded" : "billing.notices.usageVoice", { price: overagePrice })
                : t(notice.isExceeded ? "billing.notices.usageDialogsExceeded" : "billing.notices.usageDialogs");
            return (
              <Alert
                key={`usage-${notice.unit}`}
                tone={notice.isExceeded ? "danger" : "warning"}
                title={
                  notice.isExceeded
                    ? `${t("billing.notices.usageExceededTitle")} · ${t(notice.unit === "voice" ? "billing.usage.voice" : "billing.usage.dialogs")}`
                    : `${t("billing.notices.usageTitle", { percent: percent(notice.percent) })} · ${t(notice.unit === "voice" ? "billing.usage.voice" : "billing.usage.dialogs")}`
                }
              >
                {text}
              </Alert>
            );
          }
        }
      })}
    </div>
  );
}

"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconCalendar, IconCard, IconSparkles } from "@/components/icons";
import { useI18n } from "@/i18n/client";

import { quotedMoneyText } from "../_lib/billing";
import { pauseEndFor, type PauseOptions, type RetentionOffer } from "../_lib/lifecycle";
import { PauseMonthsPicker } from "./PauseMonthsPicker";

/**
 * The offer the cancel dialog makes for the chosen reason: a seasonal
 * pause (with how many months, and the dates), the next cheaper plan, or a
 * one-time credit.
 */
export function RetentionOfferPanel({
  offer,
  pause,
  months,
  onMonthsChange,
  disabled,
}: {
  offer: RetentionOffer;
  pause: PauseOptions | undefined;
  months: number;
  onMonthsChange: (months: number) => void;
  disabled: boolean;
}) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const money = (value: RetentionOffer["credit"]) => (value ? quotedMoneyText(value, format.money) : "");

  const content = (() => {
    switch (offer.kind) {
      case "pause":
        return {
          icon: <IconCalendar className="size-5" aria-hidden />,
          title: t("billingLifecycle.offers.pause.title"),
          text: t("billingLifecycle.offers.pause.description", { price: money(offer.pause_price) }),
        };
      case "downgrade":
        return {
          icon: <IconCard className="size-5" aria-hidden />,
          title: t("billingLifecycle.offers.downgrade.title"),
          text: t("billingLifecycle.offers.downgrade.description", {
            plan: offer.plan_name ?? "",
            price: money(offer.plan_price),
          }),
        };
      case "credit":
        return {
          icon: <IconSparkles className="size-5" aria-hidden />,
          title: t("billingLifecycle.offers.credit.title", { amount: money(offer.credit) }),
          text: t("billingLifecycle.offers.credit.description", { amount: money(offer.credit) }),
        };
    }
  })();

  const startsAt = pause?.starts_at ?? null;
  const endsAt = pauseEndFor(pause, months);

  return (
    <div className="space-y-4">
      <div className="flex gap-3 rounded-xl border border-accent-solid/40 bg-accent-soft p-4">
        <span className="mt-0.5 shrink-0 text-accent">{content.icon}</span>
        <div className="min-w-0 space-y-1">
          <p className="font-medium text-ink">{content.title}</p>
          <p className="text-sm text-ink-muted">{content.text}</p>
        </div>
      </div>
      {offer.kind === "pause" ? (
        <div className="space-y-2">
          <PauseMonthsPicker
            maxMonths={offer.pause_months ?? 1}
            value={months}
            onChange={onMonthsChange}
            disabled={disabled}
          />
          {startsAt && endsAt ? (
            <p className="text-sm text-ink-muted" aria-live="polite">
              {t("billingLifecycle.pause.window", { start: format.date(startsAt), until: format.date(endsAt) })}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

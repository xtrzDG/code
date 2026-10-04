"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { useI18n } from "@/i18n/client";
import type { BookingValue, OfferItem } from "@/lib/offers";

/**
 * What the booking will be worth: the service's price, or the stay's
 * nights each at its season's rate. Nothing without a booked offer.
 */
export function BookingValueLine({
  offer,
  value,
  nights,
}: {
  offer: OfferItem | null;
  value: BookingValue | null;
  /** Nights of a stay; null for a time slot. */
  nights: number | null;
}) {
  const { t, tp } = useI18n();
  const format = useBusinessFormat();
  if (!offer) {
    return null;
  }
  const money = value ? format.money(value.minor, value.currency) : null;
  const hasSeasons = offer.kind === "room_type" && (offer.seasonal_rates ?? []).length > 0;
  return (
    <div className="rounded-xl border border-line bg-surface-muted/60 px-4 py-3" aria-live="polite">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <span className="text-sm text-ink-muted">
          {t("bookings.form.value")}
          <span className="text-ink-subtle"> · </span>
          <span dir="auto" className="text-ink">
            {offer.title}
          </span>
        </span>
        {money ? (
          <span className="text-base font-semibold text-ink tabular-nums">
            {nights ? t("bookings.form.valueForStay", { value: money, nights: tp("bookings.nights", nights) }) : money}
          </span>
        ) : (
          <span className="text-sm text-ink-subtle">{t("bookings.form.valueNone")}</span>
        )}
      </div>
      {money && hasSeasons ? <p className="mt-1 text-xs text-ink-subtle">{t("bookings.form.valueSeasonsHint")}</p> : null}
    </div>
  );
}

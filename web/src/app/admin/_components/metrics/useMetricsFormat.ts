"use client";

import { useI18n } from "@/i18n/client";
import { formatMoney, formatNumber } from "@/lib/format";

import { durationParts, type WebVitalView } from "../../_lib/metrics";

type Money = { amount_minor: number; currency_code: string };

/** Numbers of the Metrics page in the interface language (lib/format.ts, lib/intl). */
export function useMetricsFormat() {
  const { t, tp, locale } = useI18n();
  const none = t("adminMetrics.kpi.none");
  return {
    number: (value: number) => formatNumber(value, locale),
    /** A share given in percent (33.33 → "33.3%"); "—" without one. */
    percent: (value: number | null | undefined) =>
      value === null || value === undefined ? none : formatNumber(value / 100, locale, { style: "percent", maximumFractionDigits: 1 }),
    money: (money: Money | null | undefined) => (money ? formatMoney(money.amount_minor, money.currency_code, locale) : none),
    /** A change of euro cents with its sign: "+€12.00", "−€3.00". */
    signedMoney: (cents: number, currency: string) =>
      `${cents > 0 ? "+" : cents < 0 ? "−" : ""}${formatMoney(Math.abs(cents), currency, locale)}`,
    duration: (seconds: number | null | undefined) => {
      if (seconds === null || seconds === undefined) {
        return none;
      }
      const { unit, count } = durationParts(seconds);
      return tp(`adminMetrics.duration.${unit}`, count);
    },
    /** A p75: milliseconds for LCP and INP, the unitless score for CLS. */
    vital: (view: Pick<WebVitalView, "metric" | "p75">) =>
      view.metric === "cls"
        ? formatNumber(view.p75 / 10_000, locale, { minimumFractionDigits: 2, maximumFractionDigits: 3 })
        : t("adminMetrics.vitals.milliseconds", { value: formatNumber(view.p75, locale) }),
  };
}

export type MetricsFormat = ReturnType<typeof useMetricsFormat>;

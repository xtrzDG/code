"use client";

import type { Schema } from "@/api/types";
import { useI18n } from "@/i18n/client";

import { formatRateDate, formatRateValue } from "../../_lib/clients";
import { RATE_SOURCE_LABELS } from "../labels";

type ExchangeRateQuote = Schema<"ExchangeRateQuote">;

/**
 * The rate a client's cost was converted with: its banks named in the
 * reader's language, its date, whether it was calculated through the euro,
 * and a warning when the daily refresh has not brought a newer one.
 */
export function RateNote({ rate, hasMargin }: { rate: ExchangeRateQuote | null | undefined; hasMargin: boolean }) {
  const { t, locale } = useI18n();
  if (!rate) {
    return hasMargin ? null : <p className="text-xs text-ink-subtle">{t("admin.detail.noRate")}</p>;
  }

  const date = formatRateDate(rate.rate_date, locale);
  const sources = (rate.sources ?? []).map((source) => t(RATE_SOURCE_LABELS[source]));
  const value = formatRateValue(rate.rate_value, locale);
  return (
    <div className="space-y-1 text-xs">
      <p className="text-ink-subtle">
        {t("admin.detail.rate", {
          rate: `1 ${rate.base_currency_code} = ${value} ${rate.quote_currency_code}`,
          source: sources.length > 0 ? sources.join(", ") : rate.source,
          date,
        })}
        {rate.is_derived ? ` ${t("admin.detail.rateDerived")}` : null}
      </p>
      {rate.is_stale ? (
        <p className="font-medium text-warning">
          {t("admin.detail.rateStale", { date })}
        </p>
      ) : null}
    </div>
  );
}

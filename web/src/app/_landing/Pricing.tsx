import type { CountryListItem, Schema } from "@/api/types";
import type { Translator } from "@/i18n/translate";
import { hasEstimatedPrice } from "@/lib/landing";

import { CountryPicker } from "./CountryPicker";
import { PlanCard } from "./PlanCard";
import { Section } from "./Section";

/** The plans of the chosen country, from GET /v1/catalog/plans. */
export function Pricing({
  translator,
  countries,
  countryCode,
  plans,
}: {
  translator: Translator;
  countries: CountryListItem[];
  countryCode: string | null;
  plans: Schema<"PlanQuoteList"> | null;
}) {
  const { t } = translator;
  const quotes = plans?.quotes ?? null;
  return (
    <Section id="pricing" title={t("landing.pricing.title")} subtitle={t("landing.pricing.subtitle")}>
      {countries.length > 0 ? (
        <div className="mb-8">
          <CountryPicker countries={countries} value={countryCode} />
        </div>
      ) : null}
      {quotes === null ? (
        <p className="rounded-2xl border border-line bg-surface p-6 text-sm text-ink-muted">{t("landing.pricing.unavailable")}</p>
      ) : quotes.length === 0 ? (
        <p className="rounded-2xl border border-line bg-surface p-6 text-sm text-ink-muted">{t("landing.pricing.empty")}</p>
      ) : (
        <>
          <ul className="grid gap-4 lg:grid-cols-3">
            {quotes.map((quote) => (
              <PlanCard key={quote.plan_key} quote={quote} translator={translator} />
            ))}
          </ul>
          <div className="mt-6 space-y-1 text-xs text-ink-subtle">
            <p>{t("landing.pricing.note")}</p>
            {plans?.exchange_rate && quotes.some(hasEstimatedPrice) ? (
              <p>
                {t("billing.plans.estimatedNote", {
                  source: plans.exchange_rate.source,
                  date: plans.exchange_rate.rate_date,
                })}
              </p>
            ) : null}
          </div>
        </>
      )}
    </Section>
  );
}

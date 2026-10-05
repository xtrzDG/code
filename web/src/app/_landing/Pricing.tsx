import type { CountryListItem, Schema } from "@/api/types";
import { Stagger } from "@/components/motion";
import type { Translator } from "@/i18n/translate";
import { hasConversion, rateDayLabel, rateSourceKey } from "@/lib/publicSite/prices";

import { CountryPicker } from "./CountryPicker";
import { PlanCard } from "./PlanCard";
import { Section } from "./Section";

type PlanQuoteList = Schema<"PlanQuoteList">;

/**
 * The plans of the chosen country, from GET /v1/catalog/plans. Prices are
 * the ones the plan is billed at; a conversion into the visitor's currency
 * is marked "≈" and the note under the cards names who set its rate (a
 * central bank, or the platform's own planning rate) and its day.
 */
export function Pricing({
  translator,
  countries,
  countryCode,
  plans,
  formAction,
}: {
  translator: Translator;
  countries: CountryListItem[];
  countryCode: string | null;
  plans: PlanQuoteList | null;
  /** The page the country picker reloads ("/ru", "/ka/for/hotel"). */
  formAction: string;
}) {
  const { t, locale } = translator;
  const quotes = plans?.quotes ?? null;
  const rate = plans?.exchange_rate ?? null;
  return (
    <Section id="pricing" title={t("landing.pricing.title")} subtitle={t("landing.pricing.subtitle")} glow="right">
      {countries.length > 0 ? (
        <div className="mb-8">
          <CountryPicker countries={countries} value={countryCode} action={formAction} />
        </div>
      ) : null}
      {quotes === null ? (
        <p className="rounded-2xl border border-line bg-surface p-6 text-sm text-ink-muted">{t("landing.pricing.unavailable")}</p>
      ) : quotes.length === 0 ? (
        <p className="rounded-2xl border border-line bg-surface p-6 text-sm text-ink-muted">{t("landing.pricing.empty")}</p>
      ) : (
        <>
          <Stagger as="ul" step={0.12} className="grid gap-4 lg:grid-cols-3">
            {quotes.map((quote) => (
              <PlanCard key={quote.plan_key} quote={quote} translator={translator} />
            ))}
          </Stagger>
          <div className="mt-6 space-y-1 text-xs text-ink-subtle" data-testid="pricing-notes">
            <p>{t("landing.pricing.note")}</p>
            {rate && hasConversion(quotes) ? (
              <p>
                {t("publicPricing.conversionNote", {
                  source: t(`publicPricing.rateSources.${rateSourceKey(rate)}`),
                  date: rateDayLabel(rate.rate_date, locale),
                })}
              </p>
            ) : null}
          </div>
        </>
      )}
    </Section>
  );
}

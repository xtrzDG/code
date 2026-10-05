import { IconCheck } from "@/components/icons";
import { StaggerItem, TiltCard } from "@/components/motion";
import { ButtonLink } from "@/components/ui";
import { CHANNEL_NAMES } from "@/components/workspace/channelNames";
import type { Translator } from "@/i18n/translate";
import { listFormat, numberFormat } from "@/lib/intl/formatters";
import { CREATE_PATH } from "@/lib/navigation";
import { planPriceLines, type PlanQuote } from "@/lib/publicSite/prices";

/**
 * One plan: the monthly price it is billed at first (the price book's lari
 * in Georgia, euros elsewhere), then the euros beside a local price or a
 * rounded conversion into the visitor's currency ("≈ $112"), what is
 * included and a call to action. It comes out of the depth with its row
 * and tilts towards the mouse.
 */
export function PlanCard({ quote, translator }: { quote: PlanQuote; translator: Translator }) {
  const { t, tp, locale } = translator;
  const prices = planPriceLines(quote, locale);
  const number = numberFormat(locale);
  const features = [
    quote.is_voice_included && quote.included_voice_minutes > 0
      ? t("billing.plans.voiceMinutes", { count: number.format(quote.included_voice_minutes) })
      : t("billing.plans.noVoice"),
    t("billing.plans.dialogs", { count: number.format(quote.included_dialogs) }),
    quote.is_voice_included ? t("billing.plans.overage", { price: prices.overage }) : null,
    t("billing.plans.setupFee", { price: prices.setupFee }),
    quote.trial_days > 0 ? tp("billing.plans.trial", quote.trial_days) : null,
  ].filter((feature): feature is string => feature !== null);
  const channels = listFormat(locale, { type: "conjunction" }).format(
    quote.channels.map((channel) => t(CHANNEL_NAMES[channel])),
  );

  return (
    <StaggerItem as="li" depth={1} className="flex">
      <TiltCard className="flex w-full flex-col rounded-2xl border border-line bg-surface p-6 shadow-lg">
        <h3 className="text-base font-semibold tracking-tight text-ink">{quote.name}</h3>
        <p className="mt-1.5 text-sm text-pretty text-ink-muted lg:min-h-20">{quote.description}</p>
        <div className="mt-6">
          <p className="flex flex-wrap items-baseline gap-x-1.5">
            <span className="text-3xl font-semibold tracking-tight text-ink tabular-nums" data-testid="plan-price">
              {prices.monthly}
            </span>
            <span className="text-sm text-ink-muted">{t("landing.pricing.perMonth")}</span>
          </p>
          {prices.secondary ? (
            <p className="mt-1 text-sm text-ink-subtle" data-testid={`plan-price-${prices.secondary.kind}`}>
              {prices.secondary.kind === "converted"
                ? t("publicPricing.converted", { price: prices.secondary.text })
                : t("landing.pricing.inEuros", { price: prices.secondary.text })}
            </p>
          ) : null}
          {quote.annual_discount_percent > 0 ? (
            <p className="mt-1 text-sm text-ink-subtle">
              {t("landing.pricing.annual", { price: prices.annual, percent: quote.annual_discount_percent })}
            </p>
          ) : null}
        </div>
        <ul className="mt-6 space-y-2.5 border-t border-line pt-5 text-sm text-ink">
          {features.map((feature) => (
            <li key={feature} className="flex gap-2.5">
              <IconCheck className="mt-0.5 size-4 shrink-0 text-accent" aria-hidden />
              <span>{feature}</span>
            </li>
          ))}
        </ul>
        <p className="mt-4 text-xs text-ink-subtle">{t("landing.pricing.channels", { list: channels })}</p>
        <div className="mt-auto pt-6">
          <ButtonLink href={CREATE_PATH} variant="secondary" fullWidth>
            {t("landing.pricing.choose", { plan: quote.name })}
          </ButtonLink>
        </div>
      </TiltCard>
    </StaggerItem>
  );
}

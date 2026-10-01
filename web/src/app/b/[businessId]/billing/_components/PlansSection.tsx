"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconCheck } from "@/components/icons";
import { Badge, Button, Card, ErrorState, LoadingBlock } from "@/components/ui";
import { CHANNEL_NAMES } from "@/components/workspace/channelNames";
import { useI18n } from "@/i18n/client";
import type { ApiError } from "@/api/errors";
import { cn } from "@/lib/cn";

import {
  hasEstimatedPrices,
  maxAnnualDiscount,
  monthlyEquivalentMinor,
  needsSubscription,
  planActions,
  planOveragePrice,
  planPrice,
  planSetupFee,
  quotedMoneyText,
  type BillingOverview,
  type BillingPeriod,
  type PlanAction,
  type PlanQuote,
} from "../_lib/billing";

export interface PlanChoice {
  quote: PlanQuote;
  period: BillingPeriod;
  action: PlanAction;
}

const ACTION_LABELS: Record<PlanAction, "billing.plans.switchTo" | "billing.plans.startTrial" | "billing.subscribe.subscribe"> = {
  switch: "billing.plans.switchTo",
  trial: "billing.plans.startTrial",
  subscribe: "billing.subscribe.subscribe",
};

/** The plans of the business's country, monthly or yearly, with the owner's action per plan. */
export function PlansSection({
  quotes,
  exchangeRate,
  error,
  onRetry,
  overview,
  period,
  onPeriodChange,
  canManage,
  onChoose,
}: {
  quotes: readonly PlanQuote[] | undefined;
  exchangeRate: { source: string; rate_date: string } | null | undefined;
  error: ApiError | null;
  onRetry: () => void;
  overview: BillingOverview;
  period: BillingPeriod;
  onPeriodChange: (period: BillingPeriod) => void;
  canManage: boolean;
  onChoose: (choice: PlanChoice) => void;
}) {
  const { t, tp, locale } = useI18n();
  const format = useBusinessFormat();
  const discount = quotes ? maxAnnualDiscount(quotes) : 0;

  return (
    <section id="billing-plans" aria-labelledby="billing-plans-title" className="scroll-mt-6 space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h2 id="billing-plans-title" className="text-lg font-semibold text-ink">
            {t("billing.plans.title")}
          </h2>
          {discount > 0 ? <p className="text-sm text-ink-muted">{t("billing.plans.description", { percent: discount })}</p> : null}
        </div>
        <fieldset className="flex rounded-xl border border-line bg-surface-muted p-1">
          <legend className="sr-only">{t("billing.plans.periodLabel")}</legend>
          {(["monthly", "annual"] as const).map((value) => (
            <label
              key={value}
              className={cn(
                "relative flex cursor-pointer items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                "has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-focus",
                period === value ? "bg-surface text-ink shadow-sm" : "text-ink-muted hover:text-ink",
              )}
            >
              <input
                type="radio"
                name="billing-period"
                value={value}
                checked={period === value}
                onChange={() => onPeriodChange(value)}
                className="sr-only"
              />
              {t(value === "annual" ? "billing.periodNames.annual" : "billing.periodNames.monthly")}
              {value === "annual" && discount > 0 ? (
                <Badge tone="success">{t("billing.plans.save", { percent: discount })}</Badge>
              ) : null}
            </label>
          ))}
        </fieldset>
      </div>

      {overview.subscription && needsSubscription(overview) && canManage ? (
        <p className="text-sm text-ink-muted">{t("billing.subscribe.resumeHint")}</p>
      ) : null}

      {error && !quotes ? (
        <Card>
          <ErrorState error={error} onRetry={onRetry} />
        </Card>
      ) : !quotes ? (
        <Card>
          <LoadingBlock label={t("common.loading")} />
        </Card>
      ) : quotes.length === 0 ? (
        <Card>
          <p className="text-sm text-ink-muted">{t("billing.plans.empty")}</p>
        </Card>
      ) : (
        <>
          <ul className="grid gap-4 lg:grid-cols-3">
            {quotes.map((quote) => {
              const { isCurrent, actions } = planActions(quote, period, overview);
              const price = planPrice(quote, period);
              const features = [
                quote.is_voice_included && quote.included_voice_minutes > 0
                  ? t("billing.plans.voiceMinutes", { count: format.number(quote.included_voice_minutes) })
                  : t("billing.plans.noVoice"),
                t("billing.plans.dialogs", { count: format.number(quote.included_dialogs) }),
                period === "annual"
                  ? t("billing.plans.setupFeeAnnual")
                  : t("billing.plans.setupFee", { price: quotedMoneyText(planSetupFee(quote), format.money) }),
                quote.is_voice_included
                  ? t("billing.plans.overage", { price: quotedMoneyText(planOveragePrice(quote), format.money) })
                  : null,
                overview.is_trial_available && quote.trial_days > 0 ? tp("billing.plans.trial", quote.trial_days) : null,
              ].filter((feature): feature is string => feature !== null);

              return (
                <li
                  key={quote.plan_key}
                  className={cn(
                    "flex flex-col rounded-2xl border bg-surface p-5 shadow-sm",
                    isCurrent ? "border-accent-solid ring-1 ring-accent-solid" : "border-line",
                  )}
                  aria-current={isCurrent ? "true" : undefined}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-base font-semibold text-ink">{quote.name}</h3>
                    {isCurrent ? <Badge tone="accent">{t("billing.plans.current")}</Badge> : null}
                  </div>
                  <p className="mt-1 min-h-10 text-sm text-ink-muted">{quote.description}</p>
                  <div className="mt-4">
                    <p className="flex flex-wrap items-baseline gap-x-1.5">
                      <span className="text-2xl font-semibold tracking-tight text-ink">{quotedMoneyText(price, format.money)}</span>
                      <span className="text-sm text-ink-muted">
                        {t(period === "annual" ? "billing.unit.annual" : "billing.unit.monthly")}
                      </span>
                    </p>
                    {period === "annual" ? (
                      <p className="mt-0.5 text-sm text-ink-muted">
                        {t("billing.plans.perMonthEquivalent", {
                          price: format.money(monthlyEquivalentMinor(price), price.money.currency_code),
                        })}
                      </p>
                    ) : null}
                  </div>
                  <ul className="mt-4 space-y-2 text-sm text-ink">
                    {features.map((feature) => (
                      <li key={feature} className="flex gap-2">
                        <IconCheck className="mt-0.5 size-4 shrink-0 text-success" aria-hidden />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <p className="mt-3 text-xs text-ink-subtle">
                    <span className="font-medium">{t("billing.plans.channelsLabel")}: </span>
                    {new Intl.ListFormat(locale, { type: "conjunction" }).format(
                      quote.channels.map((channel) => t(CHANNEL_NAMES[channel])),
                    )}
                  </p>
                  <div className="mt-auto space-y-2 pt-5">
                    {actions.length === 0 ? (
                      <Button variant="secondary" fullWidth disabled>
                        {t("billing.plans.current")}
                      </Button>
                    ) : canManage ? (
                      actions.map((action, index) => (
                        <Button
                          key={action}
                          variant={index === 0 ? "primary" : "ghost"}
                          fullWidth
                          onClick={() => onChoose({ quote, period, action })}
                        >
                          {action === "subscribe" && isCurrent
                            ? t("billing.subscribe.subscribeCurrent")
                            : t(ACTION_LABELS[action])}
                        </Button>
                      ))
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
          {exchangeRate && hasEstimatedPrices(quotes, period) ? (
            <p className="text-xs text-ink-subtle">
              {t("billing.plans.estimatedNote", { source: exchangeRate.source, date: exchangeRate.rate_date })}
            </p>
          ) : null}
        </>
      )}
    </section>
  );
}

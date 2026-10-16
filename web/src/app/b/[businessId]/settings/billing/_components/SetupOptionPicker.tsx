"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { Radio } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { quotedMoneyText, type BillingPeriod, type PlanQuote } from "../_lib/billing";
import { SETUP_OPTIONS, setupOptionFee, type SetupOption } from "../_lib/setupOptions";

/**
 * Who sets the assistant up, chosen in the subscribe dialog: the owner
 * with the guide (free) or the platform team (the plan's one-time fee with
 * the first monthly payment, included in a yearly one).
 */
export function SetupOptionPicker({
  quote,
  period,
  value,
  onChange,
  disabled,
}: {
  quote: PlanQuote;
  period: BillingPeriod;
  value: SetupOption;
  onChange: (option: SetupOption) => void;
  disabled?: boolean;
}) {
  const { t } = useI18n();
  const format = useBusinessFormat();

  const priceOf = (option: SetupOption): string => {
    const fee = setupOptionFee(quote, option, period);
    if (fee) {
      return t("billing.setupOptions.oneTime", { price: quotedMoneyText(fee, format.money) });
    }
    return option === "done_for_you" ? t("billing.setupOptions.included") : t("billing.setupOptions.free");
  };

  return (
    <fieldset className="mt-4 space-y-2">
      <legend className="mb-2 text-sm font-medium text-ink">{t("billing.setupOptions.legend")}</legend>
      {SETUP_OPTIONS.map((option) => (
        <Radio
          key={option}
          id={`setup-option-${option}`}
          name="setup-option"
          value={option}
          checked={value === option}
          disabled={disabled}
          onChange={() => onChange(option)}
          className="rounded-xl border border-line p-3 transition-colors has-[:checked]:border-accent-solid has-[:checked]:bg-accent-soft"
          label={
            <span className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
              <span className="font-medium">{t(`billing.setupOptions.${option}.title`)}</span>
              <span className="text-ink-muted tabular-nums">{priceOf(option)}</span>
            </span>
          }
          description={t(`billing.setupOptions.${option}.description`)}
        />
      ))}
    </fieldset>
  );
}

"use client";

import { useId } from "react";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { pauseMonthChoices } from "../_lib/lifecycle";

/** How many months to pause: a row of choices from one to the most allowed now. */
export function PauseMonthsPicker({
  maxMonths,
  value,
  onChange,
  disabled,
}: {
  maxMonths: number;
  value: number;
  onChange: (months: number) => void;
  disabled?: boolean;
}) {
  const { t, tp } = useI18n();
  const name = useId();
  return (
    <fieldset className="space-y-2">
      <legend className="mb-2 text-sm font-medium text-ink">{t("billingLifecycle.pause.monthsLegend")}</legend>
      <div className="flex flex-wrap gap-2">
        {pauseMonthChoices(maxMonths).map((months) => (
          <label
            key={months}
            className={cn(
              "motion-press flex min-h-9 cursor-pointer items-center rounded-lg border border-line px-3 text-sm text-ink",
              "has-[:checked]:border-accent-solid has-[:checked]:bg-accent-soft has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-focus",
              disabled && "cursor-not-allowed opacity-60",
            )}
          >
            <input
              type="radio"
              name={name}
              value={months}
              checked={value === months}
              disabled={disabled}
              onChange={() => onChange(months)}
              className="sr-only"
            />
            {tp("billingLifecycle.pause.months", months)}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

"use client";

import { useState } from "react";

import { Field, Input, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { ROI_DEFAULTS, ROI_LIMITS, clampInput, computeRoi, startingCheck } from "@/lib/publicSite/roi";
import { suggestedPlan, type RoiNiche, type RoiPlan } from "@/lib/publicSite/roiOptions";

import { RoiResult } from "./RoiResult";
import { RoiSlider } from "./RoiSlider";

/** A niche's typical check in the plan's currency, as the check field's text ("" when there is none). */
function checkText(niche: RoiNiche | undefined, plan: RoiPlan): string {
  const check = startingCheck(niche?.typicalCheckEuro ?? null, plan.monthlyEuro, plan.monthly);
  return check === null ? "" : String(check);
}

/**
 * The value calculator: the requests a business misses after hours, the
 * share that books and its average check, against the price of a plan
 * in the currency the plan is billed in. The check starts at the kind of
 * business's typical one (scaled to the plan's price level) for the
 * visitor to make their own.
 */
export function RoiCalculator({
  niches,
  plans,
  initialNicheKey,
  recommendedPlans,
}: {
  niches: readonly RoiNiche[];
  plans: readonly RoiPlan[];
  /** The kind of business chosen at first (a niche's own page). */
  initialNicheKey?: string;
  recommendedPlans?: readonly string[];
}) {
  const { t } = useI18n();
  const firstPlan = suggestedPlan(plans, recommendedPlans);
  const [nicheKey, setNicheKey] = useState(initialNicheKey ?? niches[0]?.key ?? "");
  const [planKey, setPlanKey] = useState(firstPlan?.key ?? "");
  const [missed, setMissed] = useState(ROI_DEFAULTS.missedPerMonth);
  const [afterHours, setAfterHours] = useState(ROI_DEFAULTS.afterHoursPercent);
  const [conversion, setConversion] = useState(ROI_DEFAULTS.conversionPercent);
  const niche = niches.find((candidate) => candidate.key === nicheKey);
  const plan = plans.find((candidate) => candidate.key === planKey) ?? firstPlan;
  const [check, setCheck] = useState(plan ? checkText(niche, plan) : "");
  if (!plan) {
    return null;
  }

  const averageCheck = clampInput("averageCheck", Number(check.replace(",", ".")));
  const result = computeRoi({ missedPerMonth: missed, afterHoursPercent: afterHours, averageCheck, conversionPercent: conversion }, plan.monthly);
  const percent = (value: number) => t("roi.percent", { value });
  const currencyName = t("roi.currency", { currency: plan.currency });

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]" data-testid="roi-calculator">
      <div className="space-y-6 rounded-2xl border border-line bg-surface p-6 sm:p-7">
        {niches.length > 1 ? (
          <Field label={t("roi.niche")}>
            {(control) => (
              <Select
                {...control}
                value={nicheKey}
                onChange={(event) => {
                  const next = niches.find((candidate) => candidate.key === event.target.value);
                  setNicheKey(event.target.value);
                  setCheck(checkText(next, plan));
                }}
              >
                {niches.map((option) => (
                  <option key={option.key} value={option.key}>
                    {option.name}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        ) : null}
        <RoiSlider
          label={t("roi.missed")}
          hint={t("roi.missedHint")}
          value={missed}
          valueText={String(missed)}
          min={0}
          max={1000}
          step={10}
          onChange={setMissed}
        />
        <RoiSlider
          label={t("roi.afterHours")}
          value={afterHours}
          valueText={percent(afterHours)}
          min={ROI_LIMITS.afterHoursPercent.min}
          max={ROI_LIMITS.afterHoursPercent.max}
          step={5}
          onChange={setAfterHours}
        />
        <RoiSlider
          label={t("roi.conversion")}
          value={conversion}
          valueText={percent(conversion)}
          min={ROI_LIMITS.conversionPercent.min}
          max={ROI_LIMITS.conversionPercent.max}
          step={5}
          onChange={setConversion}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label={`${t("roi.check")}, ${currencyName}`}
            hint={niche?.typicalCheckEuro === null ? t("roi.checkUnknown") : t("roi.checkHint")}
          >
            {(control) => (
              <Input
                {...control}
                inputMode="decimal"
                value={check}
                maxLength={9}
                onChange={(event) => setCheck(event.target.value.replace(/[^0-9.,]/g, ""))}
                data-testid="roi-check"
              />
            )}
          </Field>
          {plans.length > 1 ? (
            <Field label={t("roi.plan")}>
              {(control) => (
                <Select {...control} value={plan.key} onChange={(event) => setPlanKey(event.target.value)}>
                  {plans.map((option) => (
                    <option key={option.key} value={option.key}>
                      {option.name}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          ) : null}
        </div>
      </div>
      <div className="space-y-3">
        <RoiResult result={result} plan={plan} hasCheck={averageCheck > 0} />
        <p className="text-xs text-pretty text-ink-subtle">{t("roi.note")}</p>
      </div>
    </div>
  );
}

"use client";

import { useId, useState } from "react";

import { Button, Input, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import {
  currencyFractionDigits,
  decimalInputValue,
  majorToMinor,
  minorToMajor,
  moneyInputProblem,
  MONEY_INPUT_MESSAGES,
  parseDecimalInput,
} from "@/lib/format";

import { useSaveAverageCheck } from "./useValueQueries";
import { formatWholeMoney } from "./valueModel";

export interface AverageCheck {
  currency: string;
  /** The check the estimate uses (the owner's or the typical one); null: none. */
  averageCheckMinor: number | null;
  source: "owner" | "niche_default" | "none";
  /** The niche's typical check in this currency; null when unknown. */
  typicalCheckMinor: number | null;
}

type CheckProblem = keyof typeof MONEY_INPUT_MESSAGES | "positive";

function problemOf(text: string, currency: string): CheckProblem | null {
  const problem = moneyInputProblem(text, currency);
  if (problem !== null) {
    return problem;
  }
  return (parseDecimalInput(text, currency) ?? 0) > 0 ? null : "positive";
}

/**
 * The average check behind the money estimate, read and changed in place:
 * "Average check 120 GEL · typical for your kind of business  [Change]".
 * Saving reloads every value on screen; "use the typical one" clears the
 * owner's check.
 */
export function AverageCheckEditor({
  businessId,
  check,
  className,
}: {
  businessId: string;
  check: AverageCheck;
  className?: string;
}) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const inputId = useId();
  const errorId = `${inputId}-error`;
  const save = useSaveAverageCheck(businessId);
  const [draft, setDraft] = useState<string | null>(null);
  const [problem, setProblem] = useState<CheckProblem | null>(null);
  const money = (minor: number) => formatWholeMoney(minor, check.currency, locale);

  const open = () => {
    const digits = currencyFractionDigits(check.currency);
    const current = check.averageCheckMinor === null ? null : minorToMajor(check.averageCheckMinor, check.currency);
    setDraft(decimalInputValue(current, digits));
    setProblem(null);
  };

  const submit = async () => {
    if (draft === null) {
      return;
    }
    const found = problemOf(draft, check.currency);
    setProblem(found);
    if (found !== null) {
      return;
    }
    const minor = majorToMinor(parseDecimalInput(draft, check.currency) ?? 0, check.currency);
    const result = await save.run(minor);
    if (result.ok) {
      setDraft(null);
      toast.success(t("value.check.saved"));
    }
  };

  const restoreTypical = async () => {
    const result = await save.run(null);
    if (result.ok) {
      setDraft(null);
      toast.success(t("value.check.cleared"));
    }
  };

  const summary =
    check.averageCheckMinor === null
      ? t("value.check.none")
      : check.source === "owner"
        ? t("value.check.owner", { money: money(check.averageCheckMinor) })
        : t("value.check.typical", { money: money(check.averageCheckMinor) });

  if (draft === null) {
    return (
      <div className={cn("flex flex-wrap items-center gap-x-3 gap-y-1 text-sm", className)}>
        <span className="text-ink-muted">{summary}</span>
        <Button variant="ghost" size="sm" onClick={open} className="-ms-2">
          {check.averageCheckMinor === null ? t("value.check.set") : t("value.check.change")}
        </Button>
      </div>
    );
  }

  return (
    <form
      noValidate
      className={cn("space-y-2", className)}
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <label htmlFor={inputId} className="block text-sm font-medium text-ink">
        {t("value.check.inputLabel", { currency: check.currency })}
      </label>
      <div className="flex flex-wrap items-center gap-2">
        <Input
          id={inputId}
          inputMode="decimal"
          autoComplete="off"
          dir="ltr"
          autoFocus
          value={draft}
          aria-invalid={problem ? true : undefined}
          aria-describedby={problem ? errorId : `${inputId}-hint`}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setDraft(null);
            }
          }}
          className="w-32"
        />
        <Button type="submit" size="sm" disabled={save.isPending}>
          {save.isPending ? t("common.saving") : t("common.save")}
        </Button>
        <Button variant="ghost" size="sm" onClick={() => setDraft(null)}>
          {t("common.cancel")}
        </Button>
        {check.source === "owner" && check.typicalCheckMinor !== null ? (
          <Button variant="ghost" size="sm" onClick={() => void restoreTypical()} disabled={save.isPending}>
            {t("value.check.useTypical", { money: money(check.typicalCheckMinor) })}
          </Button>
        ) : null}
      </div>
      {problem ? (
        <p id={errorId} className="text-sm text-danger">
          {problem === "positive" ? t("value.check.positive") : t(MONEY_INPUT_MESSAGES[problem])}
        </p>
      ) : null}
      <p id={`${inputId}-hint`} className="text-xs text-ink-subtle">
        {t("value.check.hint")}
      </p>
    </form>
  );
}

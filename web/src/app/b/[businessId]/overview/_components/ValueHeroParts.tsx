"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { formatLocalDate, formatLocalDateRange } from "@/components/insights/dates";
import { IconClock } from "@/components/icons";
import { formatWholeMoney, periodHeading, trialTerms, type ValueModel } from "@/components/value/valueModel";
import { useI18n } from "@/i18n/client";
import type { Translator } from "@/i18n/translate";
import { cn } from "@/lib/cn";

const SHORT_DATE: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" };

/** The hero's dates: "since 5 Oct" when the period starts at the launch, else "6 Sep – 5 Oct 2026". */
export function heroPeriodText(
  model: Pick<ValueModel, "date_from" | "date_to" | "is_since_launch">,
  locale: string,
  t: Translator["t"],
): string {
  const heading = periodHeading(model);
  return heading.kind === "since"
    ? t("value.hero.since", { date: formatLocalDate(heading.from, locale, SHORT_DATE) })
    : formatLocalDateRange(heading.from, heading.to, locale);
}

/**
 * The free trial in one line, instead of a return on a plan that costs
 * nothing yet: "Free trial until 19 Oct — then GEL 510 a month".
 */
export function TrialLine({ model, className }: { model: ValueModel; className?: string }) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const terms = trialTerms(model);
  if (!terms) {
    return null;
  }
  const price = terms.priceMinor === null ? null : formatWholeMoney(terms.priceMinor, model.currency_code, locale);
  const text =
    price === null
      ? t("value.hero.trialNoPrice")
      : terms.endsAt === null
        ? t("value.hero.trial", { price })
        : t("value.hero.trialUntil", { date: format.date(terms.endsAt), price });
  return (
    <p
      data-trial-line=""
      className={cn(
        "inline-flex max-w-full items-center gap-1.5 rounded-xl border border-line bg-surface-muted px-2.5 py-1 text-xs text-ink-muted",
        className,
      )}
    >
      <IconClock className="size-3.5 shrink-0" aria-hidden />
      <span>{text}</span>
    </p>
  );
}

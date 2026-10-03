"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { formatLocalDate, formatLocalDateRange } from "@/components/insights/dates";
import { useToday } from "@/components/insights/useToday";
import { IconSparkles } from "@/components/icons";
import { TiltCard } from "@/components/motion";
import { ErrorState, Skeleton } from "@/components/ui";
import { AverageCheckEditor } from "@/components/value/AverageCheckEditor";
import { useValueOfPeriod } from "@/components/value/useValueQueries";
import { nextMonthStart, periodDays } from "@/components/value/valueModel";
import { useI18n } from "@/i18n/client";

import { ReportSummary } from "./ReportSummary";

/**
 * The month so far, live: what the monthly report on the 1st will say up
 * to now, against as many days before, with the average check behind it.
 */
export function MonthSoFarCard() {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const today = useToday(business.timezone);
  const value = useValueOfPeriod(business.id, "this_month");
  const model = value.data;

  return (
    <TiltCard
      maxDegrees={3}
      className="relative isolate overflow-hidden rounded-3xl border border-accent/25 bg-surface p-4 shadow-sm sm:p-6"
    >
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -end-24 -top-24 size-72 rounded-full bg-accent-solid/20 blur-3xl motion-safe:animate-drift" />
      </div>
      <section aria-labelledby="month-so-far" className="space-y-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="month-so-far" className="flex items-center gap-2 text-sm font-semibold text-ink">
            <IconSparkles className="size-4 text-accent" aria-hidden />
            {t("reports.monthSoFar.title")}
            {model ? (
              <span className="font-normal text-ink-muted">· {formatLocalDateRange(model.date_from, model.date_to, locale)}</span>
            ) : null}
          </h2>
          <p className="text-xs text-ink-subtle">
            {t("reports.monthSoFar.next", { date: formatLocalDate(nextMonthStart(today), locale, { day: "numeric", month: "long" }) })}
          </p>
        </div>
        {value.error && !model ? (
          <ErrorState error={value.error} onRetry={value.reload} className="py-4" />
        ) : !model ? (
          <div aria-hidden className="space-y-3">
            <Skeleton className="h-8 w-64 max-w-full" />
            <Skeleton className="h-6 w-80 max-w-full" />
          </div>
        ) : (
          <>
            <ReportSummary
              current={model.current}
              previous={model.previous}
              basis={model.value_basis}
              currency={model.currency_code}
              days={periodDays(model.date_from, model.date_to)}
            />
            <AverageCheckEditor
              businessId={business.id}
              className="border-t border-line pt-3"
              check={{
                currency: model.currency_code,
                averageCheckMinor: model.average_check_minor ?? null,
                source: model.average_check_source,
                typicalCheckMinor: model.typical_check_minor ?? null,
              }}
            />
          </>
        )}
      </section>
    </TiltCard>
  );
}

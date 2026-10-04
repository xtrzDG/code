"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { formatLocalDateRange } from "@/components/insights/dates";
import { IconArrowRight, IconChat, IconClock, IconMoon, IconSparkles } from "@/components/icons";
import { AnimatedNumber, TiltCard, TiltLayer } from "@/components/motion";
import { AverageCheckEditor } from "@/components/value/AverageCheckEditor";
import { DeltaChip } from "@/components/value/DeltaChip";
import { earningCount, formatWholeMoney, hadNoActivity, moneyFormula, periodDays, savedTime, type ValueModel } from "@/components/value/valueModel";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";
import { businessPath } from "@/lib/navigation";

/**
 * The owner's headline: what the assistant did in the period and what it
 * is worth ("22 bookings ≈ 2,640 GEL, 18 after hours, ~9 staff hours
 * saved"), each against the period before, with the average check behind
 * the money editable in place. The money tile floats in 3D under the mouse.
 */
export function ValueHero({ model, isPlaceholder }: { model: ValueModel; isPlaceholder: boolean }) {
  const { t, tp, locale } = useI18n();
  const days = periodDays(model.date_from, model.date_to);
  const { current, previous } = model;
  const count = earningCount(model.value_basis, current);
  const saved = savedTime(current.staff_minutes_saved);
  const number = (value: number) => formatNumber(value, locale);
  const isRequests = model.value_basis === "requests";
  const estimate = current.estimated_revenue_minor;
  const money = (minor: number) => formatWholeMoney(minor, model.currency_code, locale);
  const first = hadNoActivity(previous);
  const formula = moneyFormula(model.value_basis, current, model.average_check_minor);

  return (
    <section
      aria-labelledby="value-hero-title"
      aria-busy={isPlaceholder || undefined}
      className={cn(
        "relative isolate overflow-hidden rounded-3xl border border-accent/25 bg-surface p-4 shadow-sm transition-opacity sm:p-6",
        isPlaceholder && "opacity-60",
      )}
    >
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -end-20 -top-28 size-80 rounded-full bg-accent-solid/20 blur-3xl motion-safe:animate-drift" />
        <div className="absolute -start-16 -bottom-32 size-72 rounded-full bg-success/15 blur-3xl motion-safe:animate-drift motion-safe:[animation-delay:-9s]" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,var(--line)_1px,transparent_1px),linear-gradient(to_bottom,var(--line)_1px,transparent_1px)] [mask-image:radial-gradient(ellipse_at_top_right,black,transparent_70%)] bg-[size:28px_28px] opacity-40" />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="value-hero-title" className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-sm font-semibold text-ink">
          <IconSparkles className="size-4 text-accent" aria-hidden />
          {t("value.hero.title")}
          {/* On a phone the dates take their own line, so no "·" is left at its start. */}
          <span aria-hidden className="font-normal text-ink-subtle max-sm:hidden">
            ·
          </span>
          <span className="font-normal text-ink-muted max-sm:basis-full max-sm:ps-6">
            {formatLocalDateRange(model.date_from, model.date_to, locale)}
          </span>
        </h2>
        <Link
          href={businessPath(model.business_id, "overview/reports")}
          className="group inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline"
        >
          {t("value.hero.reports")}
          <IconArrowRight className="size-4 transition-transform group-hover:translate-x-0.5 rtl:-scale-x-100" aria-hidden />
        </Link>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <TiltCard
          maxDegrees={6}
          className="flex flex-col rounded-2xl border border-line bg-gradient-to-br from-accent-soft via-surface to-surface p-5 shadow-[var(--shadow-lift)] sm:p-6"
        >
          <TiltLayer depth={28}>
            <p className="text-sm font-medium text-ink-muted">
              {isRequests ? t("value.hero.requestsLabel") : t("value.hero.bookingsLabel")}
            </p>
            <p className="mt-1 flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span className="text-4xl font-semibold tracking-tight text-ink tabular-nums sm:text-5xl">
                <AnimatedNumber value={count} format={number} />
              </span>
              {estimate !== null && estimate !== undefined ? (
                <span className="bg-gradient-to-r from-accent to-success bg-clip-text text-3xl font-semibold tracking-tight text-transparent tabular-nums sm:text-4xl">
                  ≈ <AnimatedNumber value={estimate} format={money} />
                </span>
              ) : null}
            </p>
          </TiltLayer>
          <TiltLayer depth={14} className="mt-3 flex flex-wrap items-center gap-2">
            {estimate === null || estimate === undefined ? (
              <DeltaChip current={count} previous={earningCount(model.value_basis, previous)} days={days} isFirstPeriod={first} />
            ) : (
              <DeltaChip current={estimate} previous={previous.estimated_revenue_minor ?? 0} days={days} formatValue={money} isFirstPeriod={first} />
            )}
            <span className="text-xs text-ink-subtle">{isRequests ? t("value.hero.requestsHint") : t("value.hero.bookingsHint")}</span>
          </TiltLayer>
          <TiltLayer depth={8} className="mt-auto pt-4">
            <p className="text-sm text-ink-muted">
              {formula.kind === "none"
                ? t("value.hero.noMoney")
                : formula.kind === "booked"
                  ? tp("value.hero.formulaBooked", formula.valued, { count: number(formula.valued) })
                  : formula.kind === "mixed"
                    ? t("value.hero.formulaMixed", {
                        booked: money(formula.bookedMinor),
                        count: number(formula.unvalued),
                        check: money(formula.checkMinor),
                      })
                    : t("value.hero.formula", { count: number(formula.count), check: money(formula.checkMinor) })}
            </p>
          </TiltLayer>
        </TiltCard>

        <ul className="grid content-start gap-2.5">
          <Fact
            icon={<IconMoon className="size-4" />}
            text={tp("value.hero.afterHours", current.after_hours_conversation_count, {
              count: number(current.after_hours_conversation_count),
            })}
            hint={t("value.hero.afterHoursHint")}
            chip={
              <DeltaChip
                current={current.after_hours_conversation_count}
                previous={previous.after_hours_conversation_count}
                days={days}
                isFirstPeriod={first}
              />
            }
          />
          <Fact
            icon={<IconClock className="size-4" />}
            text={tp(saved.unit === "hours" ? "value.hero.hoursSaved" : "value.hero.minutesSaved", saved.count, {
              count: number(saved.count),
            })}
            hint={t("value.hero.savedHint", { replies: number(current.assistant_reply_count), calls: number(current.call_count) })}
            chip={<DeltaChip
                current={current.staff_minutes_saved}
                previous={previous.staff_minutes_saved}
                days={days}
                formatValue={(minutes) => t("reports.duration.minutes", { minutes: number(minutes) })}
                isFirstPeriod={first}
              />}
          />
          <Fact
            icon={<IconChat className="size-4" />}
            text={tp("value.hero.conversations", current.conversation_count, { count: number(current.conversation_count) })}
            hint={t("value.hero.conversationsHint")}
            chip={<DeltaChip current={current.conversation_count} previous={previous.conversation_count} days={days} isFirstPeriod={first} />}
          />
        </ul>
      </div>

      <AverageCheckEditor
        businessId={model.business_id}
        className="mt-4 border-t border-line pt-3"
        check={{
          currency: model.currency_code,
          averageCheckMinor: model.average_check_minor ?? null,
          source: model.average_check_source,
          typicalCheckMinor: model.typical_check_minor ?? null,
        }}
      />
    </section>
  );
}

function Fact({ icon, text, hint, chip }: { icon: ReactNode; text: string; hint: string; chip: ReactNode }) {
  return (
    <li className="motion-lift flex items-start gap-3 rounded-2xl border border-line bg-surface/80 p-3 backdrop-blur-sm">
      <span aria-hidden className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent">
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="text-base font-semibold text-ink tabular-nums">{text}</span>
          {chip}
        </span>
        <span className="mt-0.5 block text-xs text-ink-muted">{hint}</span>
      </span>
    </li>
  );
}

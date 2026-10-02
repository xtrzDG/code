"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { IconAlert, IconCheck, IconInfo } from "@/components/icons";
import { AnimatedNumber } from "@/components/motion";
import { ButtonLink, Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import type { Bar, NextStep, UsageLevel } from "./dashboardModel";

const STEP_STYLES: Record<NextStep["tone"], { box: string; icon: string; Icon: typeof IconInfo }> = {
  info: { box: "border-info/25 bg-info-soft", icon: "text-info", Icon: IconInfo },
  success: { box: "border-success/25 bg-success-soft", icon: "text-success", Icon: IconCheck },
  warning: { box: "border-warning/30 bg-warning-soft", icon: "text-warning", Icon: IconAlert },
  danger: { box: "border-danger/25 bg-danger-soft", icon: "text-danger", Icon: IconAlert },
};

/** The business status with the one thing the owner should do next. */
export function NextStepCard({
  step,
  status,
  href,
  note,
}: {
  step: NextStep;
  status: ReactNode;
  /** Null hides the button (the viewer cannot act there). */
  href: string | null;
  note?: string | null;
}) {
  const { t } = useI18n();
  const styles = STEP_STYLES[step.tone];
  return (
    <section
      aria-labelledby="dashboard-next-step"
      className={cn("flex flex-col gap-4 rounded-2xl border p-4 sm:flex-row sm:items-center sm:p-5", styles.box)}
    >
      <styles.Icon className={cn("hidden size-6 shrink-0 sm:block", styles.icon)} aria-hidden />
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="dashboard-next-step" className="text-base font-semibold text-ink">
            {t(step.title)}
          </h2>
          {status}
        </div>
        <p className="text-sm text-ink-muted">{t(step.description)}</p>
        {note ? <p className="text-sm font-medium text-ink">{note}</p> : null}
      </div>
      {href ? (
        <ButtonLink href={href} variant="secondary" className="self-start sm:self-center">
          {t(step.action)}
        </ButtonLink>
      ) : null}
    </section>
  );
}

/** One headline number: label, value (an <AnimatedNumber> counts up) and an optional hint line. */
export function StatTile({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4 shadow-sm sm:p-5">
      <dt className="text-sm text-ink-muted">{label}</dt>
      <dd className="mt-1 text-2xl font-semibold tracking-tight text-ink tabular-nums sm:text-3xl">{value}</dd>
      {hint ? <dd className="mt-1 text-xs text-ink-subtle">{hint}</dd> : null}
    </div>
  );
}

/** A count that needs the owner's attention, linking to where it is handled. */
export function AttentionTile({
  href,
  label,
  hint,
  count,
  formatCount,
  actionLabel,
  icon,
}: {
  href: string;
  label: string;
  hint: string;
  /** Undefined while it loads (a dash). */
  count: number | undefined;
  formatCount: (count: number) => string;
  actionLabel: string;
  icon: ReactNode;
}) {
  const isZero = count === 0;
  return (
    <Link
      href={href}
      className={cn(
        "group motion-lift flex items-center gap-4 rounded-2xl border bg-surface p-4 shadow-sm hover:border-accent/40 sm:p-5",
        isZero ? "border-line" : "border-warning/40",
      )}
    >
      <span
        className={cn(
          "flex size-11 shrink-0 items-center justify-center rounded-xl",
          isZero ? "bg-surface-muted text-ink-subtle" : "bg-warning-soft text-warning",
        )}
        aria-hidden
      >
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-medium text-ink">{label}</span>
        <span className="block text-xs text-ink-muted">{hint}</span>
      </span>
      <span className="text-2xl font-semibold text-ink tabular-nums">
        {count === undefined ? "–" : <AnimatedNumber value={count} format={formatCount} />}
      </span>
      <span className="sr-only">{actionLabel}</span>
    </Link>
  );
}

const METER_STYLES: Record<UsageLevel, { track: string; fill: string }> = {
  ok: { track: "bg-accent-soft", fill: "bg-accent-solid" },
  warning: { track: "bg-warning-soft", fill: "bg-warning" },
  over: { track: "bg-danger-soft", fill: "bg-danger-solid" },
};

/** Use of a limit (package minutes, dialogues): the fill carries the severity. */
export function Meter({
  label,
  valueText,
  percent,
  level,
  used,
  max,
}: {
  label: string;
  valueText: string;
  percent: number;
  level: UsageLevel;
  used: number;
  max: number;
}) {
  const styles = METER_STYLES[level];
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm font-medium text-ink">{label}</span>
        <span className="text-sm text-ink-muted tabular-nums">{valueText}</span>
      </div>
      <div
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-valuenow={Math.min(used, max)}
        aria-valuetext={valueText}
        className={cn("mt-2 h-2 overflow-hidden rounded-full", styles.track)}
      >
        <div className={cn("h-full rounded-full", styles.fill)} style={{ width: `${Math.min(100, percent)}%` }} />
      </div>
    </div>
  );
}

/** A ranked list of counts with proportional bars (one hue: magnitude only). */
export function BarList<Key extends string>({
  title,
  bars,
  labelOf,
  valueOf,
  emptyText,
}: {
  title: string;
  bars: readonly Bar<Key>[];
  labelOf: (key: Key) => string;
  valueOf: (bar: Bar<Key>) => string;
  emptyText: string;
}) {
  return (
    <Card title={title}>
      {bars.length === 0 ? (
        <p className="py-4 text-center text-sm text-ink-muted">{emptyText}</p>
      ) : (
        <ul className="space-y-3">
          {bars.map((bar) => (
            <li key={bar.key}>
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="min-w-0 truncate text-ink">{labelOf(bar.key)}</span>
                <span className="shrink-0 text-ink-muted tabular-nums">{valueOf(bar)}</span>
              </div>
              <div className="mt-1.5 h-2 rounded-full bg-surface-muted" aria-hidden>
                <div className="h-full rounded-full bg-accent-solid" style={{ width: `${Math.max(bar.percent, 2)}%` }} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

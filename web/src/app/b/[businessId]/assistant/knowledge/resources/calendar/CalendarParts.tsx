"use client";

import { useId, type ReactNode } from "react";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconAlert, IconCheckCircle, IconClock } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { PROBLEM_KEYS, sourceHealth, type BusySourceStatusView } from "@/lib/resourceCalendar";

/** One part of a resource's calendars: a heading, what it does, its controls. */
export function CalendarSection({
  title,
  description,
  children,
}: {
  title: ReactNode;
  description?: ReactNode;
  children: ReactNode;
}) {
  const headingId = useId();
  return (
    <section aria-labelledby={headingId} className="space-y-3 border-t border-line pt-5 first:border-t-0 first:pt-0">
      <div className="space-y-1">
        <h3 id={headingId} className="text-sm font-semibold text-ink">
          {title}
        </h3>
        {description ? <p className="text-sm text-ink-muted">{description}</p> : null}
      </div>
      {children}
    </section>
  );
}

/**
 * How the last read of a source went: when it read fine and how many busy
 * times it gave, the problem it ran into, or that it was not read yet.
 */
export function SourceStatus({ status }: { status: BusySourceStatusView | null | undefined }) {
  const { t, tp } = useI18n();
  const format = useBusinessFormat();
  const health = sourceHealth(status);
  if (health === "problem" && status?.problem) {
    return (
      <p className="flex items-start gap-1.5 text-sm text-warning" role="status">
        <IconAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
        <span>{t(PROBLEM_KEYS[status.problem])}</span>
      </p>
    );
  }
  if (health === "synced" && status?.last_synced_at) {
    return (
      <p className="flex items-start gap-1.5 text-sm text-ink-subtle">
        <IconCheckCircle className="mt-0.5 size-4 shrink-0 text-success" aria-hidden />
        <span>
          {t("calendarSync.status.synced", { time: format.dateTime(status.last_synced_at) })}
          {" · "}
          {tp("calendarSync.status.busy", status.block_count ?? 0)}
        </span>
      </p>
    );
  }
  return (
    <p className="flex items-start gap-1.5 text-sm text-ink-subtle">
      <IconClock className="mt-0.5 size-4 shrink-0" aria-hidden />
      <span>{t("calendarSync.status.never")}</span>
    </p>
  );
}

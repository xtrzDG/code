"use client";

/**
 * The first block of the Overview on a phone: what waits today, one row
 * each, with its number, opening where it is handled. Owners see who waits
 * for a person, today's bookings and questions without an answer; staff
 * see who waits, their own conversations, today's bookings and new
 * requests (they cannot open the knowledge). Counts only: nothing here is
 * an audited view of customer data. Large screens keep their tiles.
 */

import Link from "next/link";
import type { ComponentType } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconBook, IconCalendar, IconChevronRight, IconHandoff, IconInbox, IconUsers, type IconProps } from "@/components/icons";
import { formatLocalDate } from "@/components/insights/dates";
import { useToday } from "@/components/insights/useToday";
import { useAttentionCounts } from "@/components/shell/LiveEvents";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { businessPath, inboxPath } from "@/lib/navigation";

interface TodayRow {
  key: string;
  href: string;
  label: string;
  hint?: string;
  count: number | undefined;
  icon: ComponentType<IconProps>;
  /** A number above zero asks for attention (customers waiting). */
  isUrgent?: boolean;
}

function Row({ row }: { row: TodayRow }) {
  const format = useBusinessFormat();
  const { t } = useI18n();
  const Icon = row.icon;
  const isWaiting = row.isUrgent && (row.count ?? 0) > 0;
  return (
    <li>
      <Link
        href={row.href}
        data-today-row={row.key}
        className="flex min-h-14 items-center gap-3 px-4 py-2.5 transition-colors hover:bg-surface-muted active:bg-surface-muted"
      >
        <span
          aria-hidden
          className={cn(
            "flex size-9 shrink-0 items-center justify-center rounded-xl",
            isWaiting ? "bg-warning-soft text-warning" : "bg-surface-muted text-ink-subtle",
          )}
        >
          <Icon className="size-[1.125rem]" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-medium break-words text-ink">{row.label}</span>
          {row.hint ? <span className="block text-xs break-words text-ink-muted">{row.hint}</span> : null}
        </span>
        <span className={cn("text-lg font-semibold tabular-nums", isWaiting ? "text-warning" : "text-ink")}>
          {row.count === undefined ? "–" : format.number(row.count)}
        </span>
        <span className="sr-only">{t("dashboard.attention.open")}</span>
        <IconChevronRight className="size-4 shrink-0 text-ink-subtle rtl:rotate-180" aria-hidden />
      </Link>
    </li>
  );
}

export function TodayBlock({ unansweredQuestions, className }: { unansweredQuestions: number | undefined; className?: string }) {
  const { t, locale } = useI18n();
  const { business, isOwner } = useBusiness();
  const format = useBusinessFormat();
  const today = useToday(business.timezone);
  const counts = useAttentionCounts();
  const path = { business_id: business.id };
  const queue = useQuery(queryKeys.dashboard.todayQueue(business.id, today), () =>
    api.GET("/v1/businesses/{business_id}/today-queue", { params: { path } }),
  );
  const views = useQuery(
    queryKeys.dashboard.inboxViews(business.id),
    () => api.GET("/v1/businesses/{business_id}/inbox/counts", { params: { path } }),
    { enabled: !isOwner },
  );
  const bookings = queue.data;

  const waiting: TodayRow = {
    key: "needs-person",
    href: inboxPath(business.id, "needs_person"),
    label: t("dashboard.attention.openHandoffs"),
    count: counts?.needsPerson,
    icon: IconHandoff,
    isUrgent: true,
  };
  const booked: TodayRow = {
    key: "bookings",
    href: `${businessPath(business.id, "bookings")}?range=today`,
    label: t("value.queue.bookings"),
    hint: bookings
      ? t("value.queue.bookingsHint", {
          upcoming: format.number(bookings.upcoming_booking_count),
          unconfirmed: format.number(bookings.unconfirmed_booking_count),
        })
      : undefined,
    count: bookings?.booking_count,
    icon: IconCalendar,
  };
  const rows: TodayRow[] = isOwner
    ? [
        waiting,
        booked,
        {
          key: "questions",
          href: `${businessPath(business.id, "assistant/knowledge")}/questions`,
          label: t("dashboard.attention.questions"),
          count: unansweredQuestions,
          icon: IconBook,
        },
      ]
    : [
        waiting,
        { key: "mine", href: inboxPath(business.id, "mine"), label: t("value.queue.mine"), count: views.data?.mine, icon: IconUsers },
        booked,
        { key: "requests", href: inboxPath(business.id, "requests"), label: t("value.queue.requests"), count: counts?.requests, icon: IconInbox },
      ];

  return (
    <section
      aria-labelledby="overview-today"
      data-today-block=""
      className={cn("overflow-hidden rounded-2xl border border-line bg-surface", className)}
    >
      <header className="flex items-baseline justify-between gap-3 border-b border-line px-4 py-2.5">
        <h2 id="overview-today" className="text-sm font-semibold tracking-wide text-ink-muted uppercase">
          {t("overviewPhone.today.title")}
        </h2>
        <span className="text-xs text-ink-subtle">{formatLocalDate(today, locale, { weekday: "short", day: "numeric", month: "short" })}</span>
      </header>
      {!isOwner ? <p className="sr-only">{t("overviewPhone.today.staffHint")}</p> : null}
      <ul className="divide-y divide-line">
        {rows.map((row) => (
          <Row key={row.key} row={row} />
        ))}
      </ul>
    </section>
  );
}

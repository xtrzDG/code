"use client";

import Link from "next/link";
import { useState } from "react";

import { IconChevronRight, IconShield } from "@/components/icons";
import { Badge, Card, ErrorState, LoadingRegion, SkeletonCard } from "@/components/ui";
import { sourceRowName } from "@/components/value/sourceLabel";
import { formatWholeMoney } from "@/components/value/valueModel";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";
import { businessPath } from "@/lib/navigation";

import { brandTotals, topSources, type BrandLocationDashboard } from "../_lib/brands";
import { BRAND_PERIODS, useBrandDashboard, type BrandPeriod } from "../_lib/useBrands";
import { BrandLocations } from "./BrandLocations";
import { useBrandFrame } from "./BrandFrameContext";

/**
 * The brand's locations side by side over a period: conversations,
 * bookings by the assistant, work waiting for the team and (for owners)
 * the estimated value and where its customers came from. A location the
 * person does not run shows locked.
 */
export function BrandOverview() {
  const { t, locale } = useI18n();
  const { brand, isOwner } = useBrandFrame();
  const [period, setPeriod] = useState<BrandPeriod>("30d");
  const dashboard = useBrandDashboard(brand.id, period);

  if (dashboard.error && !dashboard.data) {
    return (
      <Card>
        <ErrorState error={dashboard.error} onRetry={dashboard.reload} />
      </Card>
    );
  }
  if (!dashboard.data) {
    return (
      <LoadingRegion label={t("brands.loading")}>
        <div className="space-y-6">
          <SkeletonCard lines={2} />
          <SkeletonCard lines={4} />
        </div>
      </LoadingRegion>
    );
  }

  const rows = dashboard.data.locations ?? [];
  const totals = brandTotals(rows);
  return (
    <div className={cn("space-y-6", dashboard.isPlaceholder && "opacity-60 transition-opacity")} aria-busy={dashboard.isFetching}>
      <PeriodSwitch value={period} onChange={setPeriod} />
      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Tile label={t("brands.overview.conversations")} value={formatNumber(totals.conversations, locale)} />
        <Tile label={t("brands.overview.bookings")} value={formatNumber(totals.bookings, locale)} />
        <Tile label={t("brands.overview.waiting")} value={formatNumber(totals.waiting, locale)} />
        <Tile
          label={t("brands.overview.value")}
          value={totals.value ? formatWholeMoney(totals.value.minor, totals.value.currency, locale) : "—"}
          note={isOwner ? undefined : t("brands.overview.noMoney")}
        />
      </dl>
      <ul className="space-y-3">
        {rows.map((row) => (
          <li key={row.location.business_id}>
            <LocationRow row={row} />
          </li>
        ))}
      </ul>
      {isOwner ? <BrandLocations /> : null}
    </div>
  );
}

function PeriodSwitch({ value, onChange }: { value: BrandPeriod; onChange: (period: BrandPeriod) => void }) {
  const { t } = useI18n();
  return (
    <div role="group" aria-label={t("brands.overview.periodLabel")} className="inline-flex rounded-xl border border-line bg-surface-muted p-0.5">
      {BRAND_PERIODS.map((period) => (
        <button
          key={period}
          type="button"
          aria-pressed={value === period}
          onClick={() => onChange(period)}
          className={cn(
            "inline-flex min-h-9 items-center rounded-lg px-3 text-sm font-medium transition-colors",
            value === period ? "bg-surface text-ink shadow-sm" : "text-ink-muted hover:text-ink",
          )}
        >
          {t(`brands.overview.periods.${period}`)}
        </button>
      ))}
    </div>
  );
}

function Tile({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-xl border border-line bg-surface px-4 py-3">
      <dt className="text-xs text-ink-subtle">{label}</dt>
      <dd className="mt-1 text-lg font-semibold text-ink tabular-nums">{value}</dd>
      {note ? <dd className="mt-0.5 text-xs text-ink-subtle">{note}</dd> : null}
    </div>
  );
}

function LocationRow({ row }: { row: BrandLocationDashboard }) {
  const { t, tp, locale } = useI18n();
  const { location } = row;
  const place = [location.name, location.city].filter(Boolean).join(" · ");
  if (row.is_locked) {
    return (
      <div className="flex items-center gap-3 rounded-2xl border border-dashed border-line bg-surface-muted/40 p-4">
        <IconShield className="size-5 shrink-0 text-ink-subtle" aria-hidden />
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-ink-muted" data-user-content>
            {place}
          </p>
          <p className="text-xs text-ink-subtle">{t("brands.overview.locked")}</p>
        </div>
      </div>
    );
  }
  const current = row.value?.current;
  const revenue = current?.estimated_revenue_minor;
  const sources = topSources(row.sources);
  const figures = [
    { label: t("brands.overview.conversations"), value: formatNumber(current?.conversation_count ?? 0, locale) },
    { label: t("brands.overview.bookings"), value: formatNumber(current?.assistant_booking_count ?? 0, locale) },
    { label: t("brands.overview.waiting"), value: formatNumber((row.inbox?.needs_person ?? 0) + (row.inbox?.requests ?? 0), locale) },
    {
      label: t("brands.overview.value"),
      value: revenue !== null && revenue !== undefined && row.value ? formatWholeMoney(revenue, row.value.currency_code, locale) : "—",
    },
  ];
  return (
    <Link
      href={businessPath(location.business_id)}
      className="group motion-lift flex flex-col gap-3 rounded-2xl border border-line bg-surface p-4 hover:border-line-strong hover:bg-surface-muted/40 sm:flex-row sm:items-center"
      aria-label={`${t("brands.overview.open")}: ${place}`}
    >
      <div className="min-w-0 flex-1">
        <p className="flex flex-wrap items-center gap-2">
          <span className="min-w-0 text-sm font-semibold break-words text-ink" data-user-content>
            {place}
          </span>
          {location.is_primary ? <Badge tone="neutral">{t("brands.locations.primary")}</Badge> : null}
        </p>
        {sources.length > 0 ? (
          <div className="mt-1.5 text-xs">
            <p className="text-ink-subtle">{t("brands.overview.sources")}</p>
            <ul className="mt-0.5 flex flex-wrap gap-x-3 gap-y-0.5 text-ink-muted">
              {sources.map((source, index) => (
                <li key={index} className="min-w-0 break-words">
                  {sourceRowName(source, t, tp)} <span className="font-medium text-ink tabular-nums">{formatNumber(source.conversation_count, locale)}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-1 sm:grid-cols-4">
        {figures.map((figure) => (
          <div key={figure.label} className="flex min-w-0 flex-col">
            <dt className="flex-1 text-xs leading-snug text-ink-subtle">{figure.label}</dt>
            <dd className="text-sm font-medium text-ink tabular-nums">{figure.value}</dd>
          </div>
        ))}
      </dl>
      <IconChevronRight className="hidden size-5 shrink-0 text-ink-subtle group-hover:text-accent sm:block rtl:-scale-x-100" aria-hidden />
    </Link>
  );
}

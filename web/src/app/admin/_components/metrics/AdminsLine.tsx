"use client";

import { Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { withPlatformAdmins, type AdminMetricsView, type MetricsFilters } from "../../_lib/metrics";

/**
 * Whether the platform's own admins are in the numbers: by default their
 * sign-ups and businesses are left out ("Left out: N platform admins …"),
 * a click counts them in (kept in the address) and back out.
 */
export function AdminsLine({
  view,
  filters,
  setFilters,
}: {
  view: AdminMetricsView;
  filters: MetricsFilters;
  setFilters: (filters: MetricsFilters) => void;
}) {
  const { t, tp } = useI18n();
  const growth = view.growth;
  const isIncluded = growth.are_platform_admins_included;
  const excluded = growth.excluded_platform_admins;
  const businesses = growth.excluded_admin_businesses;
  const text = isIncluded
    ? t("adminMetrics.admins.included")
    : excluded > 0 || businesses > 0
      ? [tp("adminMetrics.admins.excluded", excluded), businesses > 0 ? tp("adminMetrics.admins.excludedBusinesses", businesses) : null]
          .filter(Boolean)
          .join(" ")
      : t("adminMetrics.admins.none");

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-line bg-surface px-5 py-3">
      <div className="min-w-0 text-sm">
        <p className="font-medium text-ink" role="status">
          {text}
        </p>
        <p className="text-xs text-ink-muted">{t("adminMetrics.admins.note")}</p>
      </div>
      {isIncluded || excluded > 0 || businesses > 0 ? (
        <Button size="sm" variant="secondary" onClick={() => setFilters(withPlatformAdmins(filters, !isIncluded))}>
          {t(isIncluded ? "adminMetrics.admins.exclude" : "adminMetrics.admins.include")}
        </Button>
      ) : null}
    </div>
  );
}

"use client";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";

import type { AdminClientPage, ClientFilters, ClientHealthStatus } from "../../_lib/clients";

/** Counts over every client; a health tile filters the list by that health. */
export function SummaryTiles({
  totals,
  filters,
  setFilters,
}: {
  totals: NonNullable<AdminClientPage["totals"]>;
  filters: ClientFilters;
  setFilters: (update: (current: ClientFilters) => ClientFilters) => void;
}) {
  const { t, locale } = useI18n();
  const tiles: { label: string; value: number; health?: ClientHealthStatus; tone: string }[] = [
    { label: t("admin.summary.clients"), value: totals.client_count, tone: "text-ink" },
    { label: t("admin.summary.critical"), value: totals.critical_count, health: "critical", tone: "text-danger" },
    { label: t("admin.summary.attention"), value: totals.attention_count, health: "attention", tone: "text-warning" },
    { label: t("admin.summary.healthy"), value: totals.healthy_count, health: "healthy", tone: "text-success" },
    {
      label: t("admin.summary.losingMoney"),
      value: totals.losing_money_count,
      tone: totals.losing_money_count > 0 ? "text-danger" : "text-ink",
    },
  ];

  return (
    <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {tiles.map((tile) => {
        const content = (
          <>
            <span className="text-xs font-medium text-ink-muted">{tile.label}</span>
            <span className={cn("mt-1 block text-2xl font-semibold", tile.tone)}>{formatNumber(tile.value, locale)}</span>
          </>
        );
        const isActive = tile.health !== undefined && filters.health === tile.health;
        return (
          <li key={tile.label}>
            {tile.health ? (
              <button
                type="button"
                aria-pressed={isActive}
                onClick={() => setFilters((current) => ({ ...current, health: isActive ? "" : (tile.health ?? "") }))}
                className={cn(
                  "block w-full rounded-2xl border bg-surface px-4 py-3 text-start shadow-sm transition-colors hover:border-accent/40",
                  isActive ? "border-accent-solid ring-1 ring-accent-solid" : "border-line",
                )}
              >
                {content}
              </button>
            ) : (
              <div className="rounded-2xl border border-line bg-surface px-4 py-3 shadow-sm">{content}</div>
            )}
          </li>
        );
      })}
    </ul>
  );
}

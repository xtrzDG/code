"use client";

import { Button, Field, Input, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { countryFlag, countryName } from "@/lib/countries";

import {
  EMPTY_METRICS_FILTERS,
  PERIOD_PRESETS,
  hasMetricsFilters,
  isoDay,
  presetOf,
  presetRange,
  type AdminMetricsView,
  type MetricsFilters as Filters,
  type PeriodPreset,
} from "../../_lib/metrics";
import { useSourceName } from "./SourcesAndVitals";

/**
 * The period of sign-ups (a preset or chosen days), the country, the niche
 * and the source. Every change goes into the address at once.
 */
export function MetricsFilters({
  filters,
  setFilters,
  view,
  nicheName,
}: {
  filters: Filters;
  setFilters: (filters: Filters) => void;
  view: AdminMetricsView;
  nicheName: (key: string) => string;
}) {
  const { t, locale } = useI18n();
  const sourceName = useSourceName();
  const today = isoDay(new Date());
  const preset = presetOf(filters, today);
  const { choices } = view;

  const choosePreset = (next: PeriodPreset) => {
    if (next === "custom") {
      setFilters({ ...filters, from: view.period_start, to: view.period_end });
    } else {
      setFilters({ ...filters, ...presetRange(next, today) });
    }
  };

  return (
    <div
      role="search"
      aria-label={t("adminMetrics.filters.label")}
      className="grid gap-4 rounded-2xl border border-line bg-surface p-4 sm:grid-cols-2 lg:grid-cols-4 sm:p-5"
    >
      <Field label={t("adminMetrics.filters.period")}>
        {(control) => (
          <Select {...control} value={preset} onChange={(event) => choosePreset(event.target.value as PeriodPreset)}>
            {PERIOD_PRESETS.map((value) => (
              <option key={value} value={value}>
                {t(`adminMetrics.filters.periods.${value}`)}
              </option>
            ))}
            <option value="custom">{t("adminMetrics.filters.periods.custom")}</option>
          </Select>
        )}
      </Field>
      <Field label={t("adminMetrics.filters.country")}>
        {(control) => (
          <Select {...control} value={filters.country} onChange={(event) => setFilters({ ...filters, country: event.target.value })}>
            <option value="">{t("adminMetrics.filters.all")}</option>
            {choices.countries.map((code) => (
              <option key={code} value={code}>
                {`${countryFlag(code)} ${countryName(code, locale)}`.trim()}
              </option>
            ))}
          </Select>
        )}
      </Field>
      <Field label={t("adminMetrics.filters.niche")}>
        {(control) => (
          <Select {...control} value={filters.niche} onChange={(event) => setFilters({ ...filters, niche: event.target.value })}>
            <option value="">{t("adminMetrics.filters.all")}</option>
            {choices.niches.map((key) => (
              <option key={key} value={key}>
                {nicheName(key)}
              </option>
            ))}
          </Select>
        )}
      </Field>
      <Field label={t("adminMetrics.filters.source")}>
        {(control) => (
          <Select {...control} value={filters.source} onChange={(event) => setFilters({ ...filters, source: event.target.value })}>
            <option value="">{t("adminMetrics.filters.all")}</option>
            {choices.sources.map((source) => (
              <option key={source} value={source}>
                {sourceName(source)}
              </option>
            ))}
          </Select>
        )}
      </Field>
      {preset === "custom" ? (
        <>
          <Field label={t("adminMetrics.filters.from")}>
            {(control) => (
              <Input
                {...control}
                type="date"
                value={filters.from}
                max={filters.to || today}
                onChange={(event) => setFilters({ ...filters, from: event.target.value })}
              />
            )}
          </Field>
          <Field label={t("adminMetrics.filters.to")}>
            {(control) => (
              <Input
                {...control}
                type="date"
                value={filters.to}
                min={filters.from}
                max={today}
                onChange={(event) => setFilters({ ...filters, to: event.target.value })}
              />
            )}
          </Field>
        </>
      ) : null}
      {hasMetricsFilters(filters) ? (
        <div className="flex items-end sm:col-span-2 lg:col-span-4">
          <Button variant="ghost" size="sm" onClick={() => setFilters(EMPTY_METRICS_FILTERS)}>
            {t("adminMetrics.filters.clear")}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

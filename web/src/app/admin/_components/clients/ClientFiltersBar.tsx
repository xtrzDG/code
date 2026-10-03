"use client";

import { Field, Input, Select } from "@/components/ui";
import { IconSearch } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { countryFlag, countryName } from "@/lib/countries";

import {
  CLIENT_SORTS,
  type AdminClientPage,
  type BusinessStatus,
  type ClientFilters,
  type ClientHealthStatus,
  type ClientSort,
  type NicheKey,
} from "../../_lib/clients";
import { BUSINESS_STATUS_LABELS, HEALTH_LABELS, SORT_LABELS } from "../labels";

const HEALTH_VALUES: readonly ClientHealthStatus[] = ["critical", "attention", "healthy"];
const STATUS_VALUES: readonly BusinessStatus[] = ["onboarding", "testing", "live", "paused"];

/** Search, health, status, country and niche filters, and the sort. */
export function ClientFiltersBar({
  data,
  filters,
  setFilters,
  sort,
  setSort,
  nicheName,
}: {
  data: AdminClientPage;
  filters: ClientFilters;
  setFilters: (update: (current: ClientFilters) => ClientFilters) => void;
  sort: ClientSort;
  setSort: (sort: ClientSort) => void;
  nicheName: (key: string) => string;
}) {
  const { t, locale } = useI18n();
  return (
    <div role="search" aria-label={t("admin.filtersLabel")} className="grid gap-4 border-b border-line px-5 py-4 sm:grid-cols-2 sm:px-6 lg:grid-cols-3 xl:grid-cols-[minmax(0,2fr)_repeat(5,minmax(0,1fr))]">
      <Field label={t("admin.search")}>
        {(control) => (
          <div className="relative">
            <IconSearch className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-subtle" aria-hidden />
            <Input
              {...control}
              type="search"
              dir="auto"
              className="pl-9"
              value={filters.query}
              placeholder={t("admin.searchPlaceholder")}
              onChange={(event) => setFilters((current) => ({ ...current, query: event.target.value }))}
            />
          </div>
        )}
      </Field>
      <Field label={t("admin.healthFilter")}>
        {(control) => (
          <Select
            {...control}
            value={filters.health}
            onChange={(event) => setFilters((current) => ({ ...current, health: event.target.value as ClientHealthStatus | "" }))}
          >
            <option value="">{t("admin.all")}</option>
            {HEALTH_VALUES.map((value) => (
              <option key={value} value={value}>
                {t(HEALTH_LABELS[value])}
              </option>
            ))}
          </Select>
        )}
      </Field>
      <Field label={t("admin.statusFilter")}>
        {(control) => (
          <Select
            {...control}
            value={filters.status}
            onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value as BusinessStatus | "" }))}
          >
            <option value="">{t("admin.all")}</option>
            {STATUS_VALUES.map((value) => (
              <option key={value} value={value}>
                {t(BUSINESS_STATUS_LABELS[value])}
              </option>
            ))}
          </Select>
        )}
      </Field>
      <Field label={t("admin.serverList.country")}>
        {(control) => (
          <Select {...control} value={filters.country} onChange={(event) => setFilters((current) => ({ ...current, country: event.target.value }))}>
            <option value="">{t("admin.all")}</option>
            {(data.countries ?? []).map((code) => (
              <option key={code} value={code}>
                {`${countryFlag(code)} ${countryName(code, locale)}`}
              </option>
            ))}
          </Select>
        )}
      </Field>
      <Field label={t("admin.serverList.niche")}>
        {(control) => (
          <Select
            {...control}
            value={filters.niche}
            onChange={(event) => setFilters((current) => ({ ...current, niche: event.target.value as NicheKey | "" }))}
          >
            <option value="">{t("admin.all")}</option>
            {(data.niches ?? []).map((key) => (
              <option key={key} value={key}>
                {nicheName(key)}
              </option>
            ))}
          </Select>
        )}
      </Field>
      <Field label={t("admin.sort")}>
        {(control) => (
          <Select {...control} value={sort} onChange={(event) => setSort(event.target.value as ClientSort)}>
            {CLIENT_SORTS.map((value) => (
              <option key={value} value={value}>
                {t(SORT_LABELS[value])}
              </option>
            ))}
          </Select>
        )}
      </Field>
    </div>
  );
}

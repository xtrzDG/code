"use client";

import { SegmentedControl } from "@/components/insights/SegmentedControl";
import type { ResourceView } from "@/components/insights/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { todayIn } from "@/components/insights/dates";
import { DateField, Field, FilterSheet } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { BOOKING_RANGES, sheetFilterCount, withoutSheetFilters, type BookingFilters } from "../_lib/bookingFilters";
import { BookingFilterFields } from "./BookingFilterFields";

/**
 * The list's dates (presets, or two dates for "Choose dates"), then its
 * status, place and test bookings: in a row on large screens, behind
 * "Filters" with how many are set on phones.
 */
export function BookingFiltersBar({
  filters,
  resources,
  rangeError,
  onChange,
}: {
  filters: BookingFilters;
  resources: readonly ResourceView[];
  rangeError: string | null;
  onChange: (filters: BookingFilters) => void;
}) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const today = todayIn(business.timezone);
  return (
    <div className="space-y-3 lg:space-y-4">
      <SegmentedControl
        label={t("bookings.filters.range")}
        value={filters.range}
        onChange={(range) => onChange({ ...filters, range })}
        options={BOOKING_RANGES.map((range) => ({ value: range, label: t(`bookings.ranges.${range}`) }))}
      />
      {filters.range === "custom" ? (
        <div className="grid grid-cols-2 gap-3 sm:flex sm:flex-wrap sm:items-end">
          <Field label={t("bookings.filters.from")} error={rangeError} className="sm:w-44">
            {(control) => (
              <DateField
                {...control}
                clearable
                today={today}
                max={filters.to ?? undefined}
                value={filters.from ?? ""}
                onChange={(from) => onChange({ ...filters, from: from || null })}
              />
            )}
          </Field>
          <Field label={t("bookings.filters.to")} className="sm:w-44">
            {(control) => (
              <DateField
                {...control}
                clearable
                today={today}
                min={filters.from ?? undefined}
                value={filters.to ?? ""}
                onChange={(to) => onChange({ ...filters, to: to || null })}
              />
            )}
          </Field>
        </div>
      ) : null}
      <FilterSheet
        activeCount={sheetFilterCount(filters)}
        onClear={() => onChange(withoutSheetFilters(filters))}
        inline={
          <div className="grid grid-cols-2 gap-3 sm:flex sm:flex-wrap sm:items-end">
            <BookingFilterFields filters={filters} resources={resources} onChange={onChange} layout="row" />
          </div>
        }
      >
        <div className="space-y-4">
          <BookingFilterFields filters={filters} resources={resources} onChange={onChange} layout="sheet" />
        </div>
      </FilterSheet>
    </div>
  );
}

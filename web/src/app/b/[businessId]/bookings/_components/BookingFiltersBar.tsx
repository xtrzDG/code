"use client";

import { IncludeTestToggle } from "@/components/insights/common";
import { BOOKING_STATUS, BOOKING_STATUSES } from "@/components/insights/labels";
import { SegmentedControl } from "@/components/insights/SegmentedControl";
import type { BookingStatus, ResourceView } from "@/components/insights/types";
import { Field, Input, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { BOOKING_RANGES, type BookingFilters } from "./bookingModel";

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
  return (
    <div className="space-y-4">
      <SegmentedControl
        label={t("bookings.filters.range")}
        value={filters.range}
        onChange={(range) => onChange({ ...filters, range })}
        options={BOOKING_RANGES.map((range) => ({ value: range, label: t(`bookings.ranges.${range}`) }))}
      />
      <div className="grid grid-cols-2 gap-3 sm:flex sm:flex-wrap sm:items-end">
        {filters.range === "custom" ? (
          <>
            <Field label={t("bookings.filters.from")} error={rangeError} className="sm:w-44">
              {(control) => (
                <Input
                  {...control}
                  type="date"
                  value={filters.from ?? ""}
                  onChange={(event) => onChange({ ...filters, from: event.target.value || null })}
                />
              )}
            </Field>
            <Field label={t("bookings.filters.to")} className="sm:w-44">
              {(control) => (
                <Input
                  {...control}
                  type="date"
                  value={filters.to ?? ""}
                  onChange={(event) => onChange({ ...filters, to: event.target.value || null })}
                />
              )}
            </Field>
          </>
        ) : null}
        <Field label={t("bookings.filters.status")} className="sm:w-52">
          {(control) => (
            <Select
              {...control}
              value={filters.status ?? ""}
              onChange={(event) => onChange({ ...filters, status: (event.target.value || null) as BookingStatus | null })}
            >
              <option value="">{t("bookings.filters.allStatuses")}</option>
              {BOOKING_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {t(BOOKING_STATUS[status].label)}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label={t("bookings.filters.resource")} className="sm:w-52">
          {(control) => (
            <Select
              {...control}
              value={filters.resourceId ?? ""}
              onChange={(event) => onChange({ ...filters, resourceId: event.target.value || null })}
            >
              <option value="">{t("bookings.filters.allResources")}</option>
              {resources.map((resource) => (
                <option key={resource.id} value={resource.id}>
                  {resource.name}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <div className="col-span-2 sm:col-span-1 sm:pb-2">
          <IncludeTestToggle compact checked={filters.includeTest} onChange={(includeTest) => onChange({ ...filters, includeTest })} />
        </div>
      </div>
    </div>
  );
}

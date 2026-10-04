"use client";

import { IncludeTestToggle } from "@/components/insights/common";
import { BOOKING_STATUS, BOOKING_STATUSES } from "@/components/insights/labels";
import type { BookingStatus, ResourceView } from "@/components/insights/types";
import { Field, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import type { BookingFilters } from "../_lib/bookingFilters";

/**
 * Status, place and test bookings: in a row on large screens (`row`), one
 * under another in the phone's filter sheet (`sheet`).
 */
export function BookingFilterFields({
  filters,
  resources,
  onChange,
  layout,
}: {
  filters: BookingFilters;
  resources: readonly ResourceView[];
  onChange: (filters: BookingFilters) => void;
  layout: "row" | "sheet";
}) {
  const { t } = useI18n();
  const isRow = layout === "row";
  return (
    <>
      <Field label={t("bookings.filters.status")} className={cn(isRow && "sm:w-52")}>
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
      <Field label={t("bookings.filters.resource")} className={cn(isRow && "sm:w-52")}>
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
      <div className={cn(isRow ? "col-span-2 sm:col-span-1 sm:pb-2" : "pt-1")}>
        <IncludeTestToggle compact={isRow} checked={filters.includeTest} onChange={(includeTest) => onChange({ ...filters, includeTest })} />
      </div>
    </>
  );
}

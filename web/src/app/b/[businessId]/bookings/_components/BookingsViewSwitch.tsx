"use client";

import type { CalendarView } from "@/components/bookings/calendar/_lib/calendarTypes";
import type { ResourceView } from "@/components/insights/types";
import { SegmentedControl } from "@/components/insights/SegmentedControl";
import { useI18n } from "@/i18n/client";

import type { BookingFilters, PhoneBookingsView } from "../_lib/bookingFilters";

type PhoneChoice = PhoneBookingsView | CalendarView;
type DesktopChoice = "list" | CalendarView;

/**
 * How bookings are shown: the list, one day by place, the week's load, and
 * for places booked by the night the rooms by night. A phone keeps its
 * front-desk agenda first (Today | All | Day | Week…); a large screen opens
 * on the list (List | Day | Week…). Day shows when something is booked by
 * time, Nights when something is booked by the night.
 */
export function BookingsViewSwitch({
  filters,
  resources,
  onPhoneView,
  onCalendar,
}: {
  filters: BookingFilters;
  resources: readonly ResourceView[];
  onPhoneView: (view: PhoneBookingsView) => void;
  onCalendar: (view: CalendarView | null) => void;
}) {
  const { t } = useI18n();
  const active = resources.filter((resource) => resource.is_active);
  const hasSlots = active.length === 0 || active.some((resource) => resource.booking_unit === "time_slot");
  const hasNights = active.some((resource) => resource.booking_unit === "night");
  const calendarOptions = [
    ...(hasSlots || filters.calendar === "day" ? [{ value: "day" as const, label: t("bookingCalendar.views.day") }] : []),
    { value: "week" as const, label: t("bookingCalendar.views.week") },
    ...(hasNights || filters.calendar === "nights" ? [{ value: "nights" as const, label: t("bookingCalendar.views.nights") }] : []),
  ];
  return (
    <>
      <SegmentedControl<PhoneChoice>
        label={t("bookings.views.label")}
        value={filters.calendar ?? filters.phoneView}
        onChange={(value) => (value === "today" || value === "all" ? onPhoneView(value) : onCalendar(value))}
        options={[
          { value: "today", label: t("bookings.views.today") },
          { value: "all", label: t("bookings.views.all") },
          ...calendarOptions,
        ]}
        className="mb-4 lg:hidden"
      />
      <SegmentedControl<DesktopChoice>
        label={t("bookingCalendar.views.label")}
        value={filters.calendar ?? "list"}
        onChange={(value) => onCalendar(value === "list" ? null : value)}
        options={[{ value: "list", label: t("bookingCalendar.views.list") }, ...calendarOptions]}
        className="mb-5 w-fit max-lg:hidden"
      />
    </>
  );
}

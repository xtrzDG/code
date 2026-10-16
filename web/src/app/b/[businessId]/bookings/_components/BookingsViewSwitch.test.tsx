import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { ResourceView } from "@/components/insights/types";
import { renderInLocale } from "@/test/render";

import { DEFAULT_BOOKING_FILTERS } from "../_lib/bookingFilters";
import { BookingsViewSwitch } from "./BookingsViewSwitch";

const resource = (id: string, unit: "time_slot" | "night", isActive = true) =>
  ({ id, booking_unit: unit, is_active: isActive }) as ResourceView;

function optionsOf(group: string): string[] {
  return within(screen.getByRole("group", { name: group }))
    .getAllByRole("radio")
    .map((radio) => radio.closest("label")?.textContent ?? "");
}

describe("the bookings view switch", () => {
  it("offers Day for places booked by time and Nights for rooms", () => {
    const view = renderInLocale(
      <BookingsViewSwitch filters={DEFAULT_BOOKING_FILTERS} resources={[resource("a", "night")]} onPhoneView={vi.fn()} onCalendar={vi.fn()} />,
    );
    expect(optionsOf("Show bookings as")).toEqual(["List", "Week", "Nights"]);
    expect(optionsOf("What to show")).toEqual(["Today", "All bookings", "Week", "Nights"]);

    view.rerender(
      <BookingsViewSwitch
        filters={DEFAULT_BOOKING_FILTERS}
        resources={[resource("a", "time_slot"), resource("b", "night", false)]}
        onPhoneView={vi.fn()}
        onCalendar={vi.fn()}
      />,
    );
    expect(optionsOf("Show bookings as")).toEqual(["List", "Day", "Week"]);
  });

  it("opens a view, and the list or today's agenda again", async () => {
    const onPhoneView = vi.fn();
    const onCalendar = vi.fn();
    renderInLocale(
      <BookingsViewSwitch
        filters={{ ...DEFAULT_BOOKING_FILTERS, calendar: "day" }}
        resources={[]}
        onPhoneView={onPhoneView}
        onCalendar={onCalendar}
      />,
    );
    const desktop = within(screen.getByRole("group", { name: "Show bookings as" }));
    expect(desktop.getByRole("radio", { name: "Day" })).toHaveProperty("checked", true);
    await userEvent.click(desktop.getByRole("radio", { name: "Week" }));
    expect(onCalendar).toHaveBeenLastCalledWith("week");
    await userEvent.click(desktop.getByRole("radio", { name: "List" }));
    expect(onCalendar).toHaveBeenLastCalledWith(null);
    await userEvent.click(within(screen.getByRole("group", { name: "What to show" })).getByRole("radio", { name: "Today" }));
    expect(onPhoneView).toHaveBeenLastCalledWith("today");
  });
});

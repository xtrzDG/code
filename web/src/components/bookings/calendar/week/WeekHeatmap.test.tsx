import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { renderInLocale } from "@/test/render";

import type { CalendarGrid } from "../_lib/calendarTypes";
import { WeekHeatmap } from "./WeekHeatmap";

const DATES = ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09", "2026-10-10", "2026-10-11"];

function grid(): CalendarGrid {
  const place = (id: string, name: string, unit: "time_slot" | "night") => ({
    id,
    name,
    kind: unit === "night" ? ("room" as const) : ("table" as const),
    booking_unit: unit,
    capacity: 2,
    unit_count: 2,
    is_active: true,
  });
  return {
    date_from: DATES[0] ?? "",
    date_to: DATES[6] ?? "",
    timezone: "Asia/Tbilisi",
    is_truncated: false,
    bookings: [],
    places: [place("res_terrace", "Terrace", "time_slot"), place("res_deluxe", "Deluxe", "night")],
    days: DATES.map((date, index) => ({
      date,
      business_ranges: [],
      places: [
        {
          resource_id: "res_terrace",
          is_open: index !== 0,
          booking_count: index,
          open_unit_minutes: index === 0 ? 0 : 1200,
          booked_unit_minutes: index * 120,
        },
        { resource_id: "res_deluxe", is_open: true, booking_count: 1, open_units: 2, booked_units: 1 },
      ],
    })),
  };
}

describe("the week's heatmap", () => {
  it("shows each place's load per day, closed days and rooms taken", () => {
    renderInLocale(<WeekHeatmap grid={grid()} today="2026-10-07" onOpenDay={() => undefined} />);
    const table = screen.getByRole("table", { name: /^How full each place is/ });
    expect(within(table).getByRole("button", { name: /^Terrace, Monday, October 5: Closed/ })).toBeDefined();
    expect(within(table).getByRole("button", { name: /^Terrace, Wednesday, October 7: 20% booked, 2 bookings$/ })).toBeDefined();
    expect(within(table).getAllByRole("button", { name: /^Deluxe, .*: 1 of 2 rooms taken, 1 booking$/ })).toHaveLength(7);
    expect(within(table).getByRole("button", { name: /^All places, Monday, October 5: 50% booked/ })).toBeDefined();
  });

  it("is one tab stop the arrows move through, and a cell opens its day or nights", async () => {
    const onOpenDay = vi.fn();
    renderInLocale(<WeekHeatmap grid={grid()} today="2026-10-07" onOpenDay={onOpenDay} />);
    const cells = screen.getAllByRole("button");
    expect(cells.filter((cell) => cell.tabIndex === 0)).toHaveLength(1);

    const first = cells[0];
    first?.focus();
    fireEvent.keyDown(first as HTMLElement, { key: "ArrowRight" });
    expect(document.activeElement?.getAttribute("data-heat-cell")).toBe("0-1");
    fireEvent.keyDown(document.activeElement as HTMLElement, { key: "ArrowDown" });
    fireEvent.keyDown(document.activeElement as HTMLElement, { key: "ArrowDown" });
    fireEvent.keyDown(document.activeElement as HTMLElement, { key: "End" });
    expect(document.activeElement?.getAttribute("data-heat-cell")).toBe("2-6");

    await userEvent.keyboard("{Enter}");
    expect(onOpenDay).toHaveBeenLastCalledWith("2026-10-11", "nights");
    await userEvent.click(screen.getByRole("button", { name: /^Terrace, Tuesday, October 6/ }));
    expect(onOpenDay).toHaveBeenLastCalledWith("2026-10-06", "day");
  });
});

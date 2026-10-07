import { describe, expect, it } from "vitest";

import { bookingFixture } from "@/app/b/[businessId]/bookings/_lib/bookingFixtures";

import { durationOf, isSameSpot, keyboardTarget, moveBody, movedView, placeOf } from "./calendarMoves";
import type { MoveTarget } from "./calendarTypes";

const dinner = bookingFixture({ date: "2026-10-06", time: "19:00", end_date: "2026-10-06", end_time: "21:00", resource_id: "res_window", resource_name: "Window table" });
const stay = bookingFixture({ date: "2026-10-06", time: null, end_date: "2026-10-08", end_time: null, resource_id: "res_deluxe", resource_name: "Deluxe" });
const terrace: MoveTarget = { resourceId: "res_terrace", resourceName: "Terrace", date: "2026-10-06", time: "23:00" };
const places = [
  { id: "res_window", name: "Window table" },
  { id: "res_terrace", name: "Terrace" },
];
const bounds = { firstMinute: 12 * 60, lastMinute: 22 * 60, firstDate: "2026-10-06", lastDate: "2026-10-19" };

describe("a moved booking", () => {
  it("keeps its length, over midnight too", () => {
    expect(durationOf(dinner)).toBe(120);
    const moved = movedView(dinner, terrace);
    expect([moved.resource_name, moved.date, moved.time, moved.end_date, moved.end_time]).toEqual([
      "Terrace",
      "2026-10-06",
      "23:00",
      "2026-10-07",
      "01:00",
    ]);
  });

  it("keeps a stay's nights", () => {
    const moved = movedView(stay, { resourceId: "res_standard", resourceName: "Standard", date: "2026-10-10", time: null });
    expect([moved.resource_id, moved.date, moved.end_date, moved.time]).toEqual(["res_standard", "2026-10-10", "2026-10-12", null]);
    expect(durationOf(stay)).toBe(60);
  });

  it("asks the API to move it only from the start the calendar showed, and Undo goes back there", () => {
    expect(moveBody(dinner, terrace)).toEqual({
      new_date: "2026-10-06",
      new_time: "23:00",
      new_resource_id: "res_terrace",
      expected_date: "2026-10-06",
      expected_time: "19:00",
    });
    expect(placeOf(dinner)).toEqual({ resourceId: "res_window", resourceName: "Window table", date: "2026-10-06", time: "19:00" });
    expect(isSameSpot(dinner, placeOf(dinner))).toBe(true);
    expect(isSameSpot(dinner, terrace)).toBe(false);
    expect(moveBody(stay, placeOf(stay)).expected_time).toBeNull();
  });
});

describe("the keyboard", () => {
  const at = placeOf(dinner);

  it("moves a booking by a quarter of an hour and to the place beside", () => {
    expect(keyboardTarget(at, "ArrowDown", places, bounds, "ArrowRight")?.time).toBe("19:15");
    expect(keyboardTarget(at, "ArrowUp", places, bounds, "ArrowRight")?.time).toBe("18:45");
    expect(keyboardTarget(at, "ArrowRight", places, bounds, "ArrowRight")?.resourceName).toBe("Terrace");
    expect(keyboardTarget(at, "ArrowLeft", places, bounds, "ArrowRight")).toBeNull();
    // Right to left: the left arrow goes to the next column.
    expect(keyboardTarget(at, "ArrowLeft", places, bounds, "ArrowLeft")?.resourceName).toBe("Terrace");
    expect(keyboardTarget(at, "Enter", places, bounds, "ArrowRight")).toBeNull();
  });

  it("stops at the grid's first and last quarter", () => {
    expect(keyboardTarget({ ...at, time: "12:00" }, "ArrowUp", places, bounds, "ArrowRight")).toBeNull();
    expect(keyboardTarget({ ...at, time: "22:00" }, "ArrowDown", places, bounds, "ArrowRight")).toBeNull();
  });

  it("moves a stay by a night, and between rooms", () => {
    const rooms = [
      { id: "res_deluxe", name: "Deluxe" },
      { id: "res_standard", name: "Standard" },
    ];
    const here = placeOf(stay);
    expect(keyboardTarget(here, "ArrowRight", rooms, bounds, "ArrowRight")?.date).toBe("2026-10-07");
    expect(keyboardTarget(here, "ArrowLeft", rooms, bounds, "ArrowRight")).toBeNull();
    expect(keyboardTarget(here, "ArrowDown", rooms, bounds, "ArrowRight")?.resourceId).toBe("res_standard");
    expect(keyboardTarget(here, "ArrowUp", rooms, bounds, "ArrowRight")).toBeNull();
    expect(keyboardTarget({ ...here, date: "2026-10-19" }, "ArrowRight", rooms, bounds, "ArrowRight")).toBeNull();
    expect(keyboardTarget(here, "Escape", rooms, bounds, "ArrowRight")).toBeNull();
  });
});

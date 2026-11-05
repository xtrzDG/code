import { describe, expect, it } from "vitest";

import { bookingActionLayout, bookingActions, hasStarted, localNowIn } from "./bookingList";

describe("booking actions before and after the start", () => {
  it("offer completed and no-show only once the booking has started", () => {
    expect(bookingActions("confirmed", false)).toEqual({ confirm: false, complete: false, noShow: false, reschedule: true, cancel: true });
    expect(bookingActions("confirmed", true)).toEqual({ confirm: false, complete: true, noShow: true, reschedule: true, cancel: true });
  });

  it("know the start in the business's local time", () => {
    // 10:30 UTC is 14:30 in Tbilisi.
    const now = localNowIn("Asia/Tbilisi", new Date(Date.UTC(2026, 9, 3, 10, 30)));
    expect(now).toBe("2026-10-03T14:30");
    expect(hasStarted({ date: "2026-10-03", time: "14:00" }, now)).toBe(true);
    expect(hasStarted({ date: "2026-10-03", time: "14:30:00" }, now)).toBe(true);
    expect(hasStarted({ date: "2026-10-03", time: "15:00" }, now)).toBe(false);
    expect(hasStarted({ date: "2026-10-04", time: null }, now)).toBe(false);
    // A whole-day booking (a stay) starts at midnight.
    expect(hasStarted({ date: "2026-10-03", time: null }, now)).toBe(true);
  });
});

describe("booking action layout", () => {
  it("make confirming a request the one main action", () => {
    expect(bookingActionLayout(bookingActions("pending", false))).toEqual({ primary: "confirm", more: ["reschedule", "edit", "cancel"] });
  });

  it("make 'completed' the main action once a confirmed booking started", () => {
    expect(bookingActionLayout(bookingActions("confirmed", true))).toEqual({
      primary: "complete",
      more: ["noShow", "reschedule", "edit", "cancel"],
    });
  });

  it("leave editing first for an upcoming confirmed booking, cancelling last", () => {
    expect(bookingActionLayout(bookingActions("confirmed", false))).toEqual({ primary: "edit", more: ["reschedule", "cancel"] });
  });

  it("offer only editing for a finished booking", () => {
    expect(bookingActionLayout(bookingActions("completed", true))).toEqual({ primary: "edit", more: [] });
  });
});

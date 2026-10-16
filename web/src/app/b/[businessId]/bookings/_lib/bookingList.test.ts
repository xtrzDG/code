import { describe, expect, it } from "vitest";

import { bookingActions, customerLanguage, groupBookingsByDate, nightsOf, reminderState } from "./bookingList";
import { groupSlotsByResource } from "./manualBooking";
import { booking } from "./bookingFixtures";

describe("grouping", () => {
  it("groups by day and orders by time", () => {
    const days = groupBookingsByDate([
      booking("late", "2026-10-02", "20:00"),
      booking("next", "2026-10-03", "12:00"),
      booking("early", "2026-10-02", "09:30"),
    ]);
    expect(days.map((day) => [day.date, day.bookings.map((item) => item.id)])).toEqual([
      ["2026-10-02", ["early", "late"]],
      ["2026-10-03", ["next"]],
    ]);
    expect(groupBookingsByDate([booking("a", "2026-09-01", null), booking("b", "2026-09-02", null)], { newestFirst: true })[0]?.date).toBe(
      "2026-09-02",
    );
  });

  it("counts nights of stays", () => {
    expect(nightsOf({ date: "2026-10-01", end_date: "2026-10-04" })).toBe(3);
    expect(nightsOf({ date: "2026-10-01", end_date: "2026-10-01" })).toBe(0);
  });
});

describe("actions", () => {
  it("allow changes only to active bookings", () => {
    expect(bookingActions("pending")).toEqual({ confirm: true, complete: true, noShow: true, reschedule: true, cancel: true });
    expect(bookingActions("confirmed").confirm).toBe(false);
    expect(Object.values(bookingActions("cancelled")).some(Boolean)).toBe(false);
    expect(Object.values(bookingActions("completed")).some(Boolean)).toBe(false);
  });
});

describe("booking details", () => {
  it("uses the customer's language when the business speaks it", () => {
    const business = { languages: ["ka", "en"], default_language: "ka" };
    expect(customerLanguage({ language: "en" }, business)).toBe("en");
    expect(customerLanguage({ language: "de" }, business)).toBe("ka");
    expect(customerLanguage({ language: null }, business)).toBe("ka");
  });

  it("tells whether the reminder went out or is still to come", () => {
    const upcoming = { ...booking("a", "2026-10-03", "20:00"), status: "confirmed" as const };
    expect(reminderState(upcoming, "2026-10-01")).toBe("pending");
    expect(reminderState({ ...upcoming, reminder_sent_at: 1 }, "2026-10-01")).toBe("sent");
    expect(reminderState({ ...upcoming, status: "cancelled" }, "2026-10-01")).toBe("none");
    expect(reminderState(upcoming, "2026-10-04")).toBe("none");
  });

  it("groups whole-day slots by place in the order they come", () => {
    const slot = (resource: string, time: string) => ({
      resource_id: resource,
      resource_name: resource.toUpperCase(),
      booking_unit: "time_slot" as const,
      date: "2026-10-03",
      time,
    });
    const groups = groupSlotsByResource([slot("t2", "12:00"), slot("t4", "12:00"), slot("t2", "12:30")]);
    expect(groups.map((group) => [group.resourceName, group.slots.map((item) => item.time)])).toEqual([
      ["T2", ["12:00", "12:30"]],
      ["T4", ["12:00"]],
    ]);
  });
});

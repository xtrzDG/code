import { describe, expect, it } from "vitest";

import { bookingFixture } from "./bookingFixtures";
import { timeOfMoment, todayAgenda } from "./todayAgenda";

const NOW = "2026-10-05T19:30";

describe("today's agenda", () => {
  it("lists arrivals by time, counts the day and leaves cancelled bookings out", () => {
    const agenda = todayAgenda(
      [
        bookingFixture({ id: "late", time: "21:00", contact_name: "Late" }),
        bookingFixture({ id: "early", time: "18:00", contact_name: "Early", status: "completed" }),
        bookingFixture({ id: "gone", time: "19:00", status: "cancelled" }),
        bookingFixture({ id: "now", time: "19:30", contact_name: "Now", status: "pending" }),
        bookingFixture({ id: "missed", time: "17:00", status: "no_show" }),
      ],
      NOW,
    );

    expect(agenda.entries.map((entry) => entry.booking.id)).toEqual(["missed", "early", "now", "late"]);
    expect(agenda.counts).toEqual({ toCome: 2, arrived: 1, missed: 1, cancelled: 1 });
    // The line "now" goes before the first booking still ahead.
    expect(agenda.nowIndex).toBe(3);
  });

  it("allows Arrived and No-show only for active bookings whose start has come", () => {
    const agenda = todayAgenda(
      [
        bookingFixture({ id: "started", time: "19:30" }),
        bookingFixture({ id: "ahead", time: "19:31" }),
        bookingFixture({ id: "done", time: "18:00", status: "completed" }),
      ],
      NOW,
    );
    const canMark = Object.fromEntries(agenda.entries.map((entry) => [entry.booking.id, entry.canMark]));

    expect(canMark).toEqual({ done: false, started: true, ahead: false });
    expect(agenda.entries.find((entry) => entry.booking.id === "done")?.isActive).toBe(false);
  });

  it("draws no now line when every booking is ahead or every one has started", () => {
    expect(todayAgenda([bookingFixture({ time: "20:00" }), bookingFixture({ time: "21:00" })], NOW).nowIndex).toBeNull();
    expect(todayAgenda([bookingFixture({ time: "12:00" }), bookingFixture({ time: "13:00" })], NOW).nowIndex).toBeNull();
    expect(todayAgenda([], NOW)).toEqual({ entries: [], nowIndex: null, counts: { toCome: 0, arrived: 0, missed: 0, cancelled: 0 } });
  });

  it("puts a stay without a time first and orders equal times by name", () => {
    const agenda = todayAgenda(
      [
        bookingFixture({ id: "b", time: "20:00", contact_name: "Beka" }),
        bookingFixture({ id: "a", time: "20:00", contact_name: "Ana" }),
        bookingFixture({ id: "stay", time: null, contact_name: null }),
      ],
      NOW,
    );

    expect(agenda.entries.map((entry) => entry.booking.id)).toEqual(["stay", "a", "b"]);
  });

  it("reads the time of a local moment", () => {
    expect(timeOfMoment(NOW)).toBe("19:30");
  });
});

import { describe, expect, it } from "vitest";

import { ApiError, describeError } from "@/api/errors";
import { en } from "@/i18n/messages/en";
import { createTranslator } from "@/i18n/translate";

import {
  bookingSystemErrors,
  busyRange,
  CALENDAR_REFUSAL_MESSAGES,
  feedAddressError,
  googleChoiceValue,
  linkedGoogleEntry,
  PROBLEM_KEYS,
  sourceCount,
  sortGoogleCalendars,
  sourceHealth,
  summaryLine,
  type ResourceCalendarView,
} from "./resourceCalendar";

const view = (patch: Partial<ResourceCalendarView> = {}): ResourceCalendarView => ({
  business_id: "business_1",
  resource_id: "resource_1",
  resource_name: "Sea view",
  google: { is_available: true, is_connected: true, calendar_id: null, status: null },
  ical_imports: [],
  ical_export: { is_on: false },
  booking_system: null,
  booking_system_kinds: ["cal_com"],
  upcoming_busy_times: [],
  ...patch,
});

describe("resource calendars", () => {
  it("tells a source's health from its last read", () => {
    expect(sourceHealth(null)).toBe("waiting");
    expect(sourceHealth({ block_count: 0 })).toBe("waiting");
    expect(sourceHealth({ block_count: 2, last_synced_at: 10 })).toBe("synced");
    expect(sourceHealth({ block_count: 2, last_synced_at: 10, problem: "timeout" })).toBe("problem");
  });

  it("checks an iCal address before sending it", () => {
    expect(feedAddressError("   ")).toBe("calendarSync.ical.required");
    expect(feedAddressError("ftp://example.com/feed.ics")).toBe("calendarSync.ical.invalid");
    expect(feedAddressError("https://")).toBe("calendarSync.ical.invalid");
    expect(feedAddressError("https://a b.com/x.ics")).toBe("calendarSync.ical.invalid");
    expect(feedAddressError(`https://example.com/${"x".repeat(2100)}`)).toBe("calendarSync.ical.invalid");
    expect(feedAddressError(" https://www.airbnb.com/calendar/ical/1.ics?s=abc ")).toBeNull();
    expect(feedAddressError("WEBCAL://calendar.example.com/feed")).toBeNull();
  });

  it("checks a booking system's event type and key", () => {
    expect(bookingSystemErrors("", "")).toEqual({
      eventType: "calendarSync.bookingSystem.eventTypeRequired",
      apiKey: "calendarSync.bookingSystem.apiKeyRequired",
    });
    expect(bookingSystemErrors("12 34", "cal_live_x")).toEqual({
      eventType: "calendarSync.bookingSystem.eventTypeInvalid",
    });
    expect(bookingSystemErrors(" 1203845 ", "cal_live_x")).toEqual({});
  });

  it("finds a linked calendar in the account's list, its own calendar as primary", () => {
    const own = { calendar_id: "owner@example.com", name: "Owner", access_role: "owner", is_primary: true };
    const room = { calendar_id: "a@group", name: "Room 1", access_role: "reader", is_primary: false };
    expect(googleChoiceValue(own)).toBe("primary");
    expect(googleChoiceValue(room)).toBe("a@group");
    expect(linkedGoogleEntry("primary", [room, own])).toBe(own);
    expect(linkedGoogleEntry("owner@example.com", [room, own])).toBe(own);
    expect(linkedGoogleEntry("a@group", [room, own])).toBe(room);
    expect(linkedGoogleEntry("gone@group", [room, own])).toBeUndefined();
    const zed = { ...room, calendar_id: "z@group", name: "Zed" };
    expect(sortGoogleCalendars([zed, room, own], "en").map((entry) => entry.name)).toEqual(["Owner", "Room 1", "Zed"]);
  });

  it("writes a busy time as one line, the end's date only on another day", () => {
    const format = {
      date: (value: number) => `d${Math.floor(value / 100)}`,
      dateTime: (value: number) => `dt${value}`,
      time: (value: number) => `t${value}`,
    };
    expect(busyRange({ starts_at: 101, ends_at: 150 }, format)).toBe("dt101 – t150");
    expect(busyRange({ starts_at: 101, ends_at: 250 }, format)).toBe("dt101 – dt250");
  });

  it("counts the sources that block a resource", () => {
    expect(sourceCount(view())).toBe(0);
    expect(
      sourceCount(
        view({
          google: { is_available: true, is_connected: true, calendar_id: "primary", status: { block_count: 0 } },
          ical_imports: [
            { feed_id: "ical_import_1", host: "www.airbnb.com", added_at: 1, status: { block_count: 1 } },
          ],
          booking_system: {
            kind: "cal_com",
            external_resource_id: "1",
            added_at: 1,
            status: { block_count: 0 },
            write_status: {},
          },
        }),
      ),
    ).toBe(3);
  });

  it("sums a resource's calendars in one line, problems first", () => {
    const base = { resource_id: "resource_1", source_count: 0, problem_count: 0, is_export_on: false };
    expect(summaryLine(undefined)).toBeNull();
    expect(summaryLine(base)).toBeNull();
    expect(summaryLine({ ...base, is_export_on: true })).toEqual({ key: "calendarSync.row.shared", tone: "neutral" });
    expect(summaryLine({ ...base, source_count: 2 })).toEqual({ key: "calendarSync.row.sources", count: 2, tone: "neutral" });
    expect(summaryLine({ ...base, source_count: 2, problem_count: 1 })).toEqual({
      key: "calendarSync.row.problems",
      count: 1,
      tone: "warning",
    });
  });

  it("has a text for every problem and refusal", () => {
    const { t } = createTranslator("en", en);
    for (const key of Object.values(PROBLEM_KEYS)) {
      expect(t(key)).not.toBe(key);
    }
    const refusal = new ApiError({
      status: 422,
      code: "validation_failed",
      detail: "Refused",
      reasons: [{ code: "feed_limit", message: "limit", details: [] }],
    });
    expect(describeError(refusal, t, undefined, CALENDAR_REFUSAL_MESSAGES).title).toBe(
      "A resource imports at most 5 calendars.",
    );
    expect(Object.keys(CALENDAR_REFUSAL_MESSAGES)).toHaveLength(10);
  });
});

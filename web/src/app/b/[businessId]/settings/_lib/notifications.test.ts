import { describe, expect, it } from "vitest";

import { en } from "@/i18n/messages/en";
import { createTranslator } from "@/i18n/translate";

import {
  contactCheckOutcome,
  findThisDevice,
  isEverything,
  isSamePreferences,
  preferencesForm,
  preferencesFromForm,
  preferencesSummary,
  quietHoursErrors,
  toggleEvent,
  type NotificationCheckResult,
  type PushDevice,
} from "./notifications";

const { t } = createTranslator("en", en);

describe("notification preferences", () => {
  it("start from every event at any hour", () => {
    expect(preferencesForm(null)).toEqual({
      events: ["handoff", "lead", "booking"],
      hasQuietHours: false,
      from: "22:00",
      until: "08:00",
    });
    expect(preferencesForm({ events: ["booking", "handoff"], quiet_hours: { starts_at: "23:00", ends_at: "07:00" } })).toEqual({
      events: ["handoff", "booking"],
      hasQuietHours: true,
      from: "23:00",
      until: "07:00",
    });
  });

  it("switch events on and off in their usual order", () => {
    expect(toggleEvent(["booking"], "handoff", true)).toEqual(["handoff", "booking"]);
    expect(toggleEvent(["handoff", "booking"], "handoff", false)).toEqual(["booking"]);
  });

  it("check the quiet hours only while they are on", () => {
    const form = { events: [], hasQuietHours: true, from: "22:00", until: "22:00" } as const;
    expect(quietHoursErrors({ ...form, events: [] })).toEqual({ until: "same" });
    expect(quietHoursErrors({ ...form, events: [], from: "25:00", until: "7:00" })).toEqual({ from: "format", until: "format" });
    expect(quietHoursErrors({ ...form, events: [], hasQuietHours: false })).toEqual({});
    expect(quietHoursErrors({ ...form, events: [], until: "08:00" })).toEqual({});
  });

  it("are sent as the API takes them", () => {
    expect(preferencesFromForm({ events: ["lead"], hasQuietHours: false, from: "22:00", until: "08:00" })).toEqual({
      events: ["lead"],
      quiet_hours: null,
    });
    expect(preferencesFromForm({ events: [], hasQuietHours: true, from: "13:00", until: "14:00" })).toEqual({
      events: [],
      quiet_hours: { starts_at: "13:00", ends_at: "14:00" },
    });
  });

  it("read as one line", () => {
    expect(isEverything(null)).toBe(true);
    expect(isEverything({ events: ["lead", "handoff", "booking"] })).toBe(true);
    expect(preferencesSummary(t, null)).toBe("Everything, at any time");
    expect(preferencesSummary(t, { events: ["handoff", "booking"], quiet_hours: { starts_at: "22:00", ends_at: "08:00" } })).toBe(
      "Only: handoffs, bookings · quiet 22:00–08:00",
    );
    expect(preferencesSummary(t, { events: [] })).toBe("Nothing");
    expect(preferencesSummary(t, { quiet_hours: { starts_at: "13:00", ends_at: "14:00" } })).toBe("quiet 13:00–14:00");
  });

  it("compare by meaning", () => {
    expect(isSamePreferences({ events: ["booking", "lead"] }, { events: ["lead", "booking"], quiet_hours: null })).toBe(true);
    expect(isSamePreferences({}, { events: ["handoff", "lead", "booking"] })).toBe(true);
    expect(isSamePreferences({}, { quiet_hours: { starts_at: "22:00", ends_at: "08:00" } })).toBe(false);
  });
});

describe("notification checks and devices", () => {
  const result = (status: "delivered" | "pending" | "dead", isSimulated = false): NotificationCheckResult => ({
    delivery: { status, attempted_at: 1 },
    is_simulated: isSimulated,
  });

  it("tell how a check went", () => {
    expect(contactCheckOutcome(result("delivered"))).toEqual({ tone: "success", key: "notifications.contacts.testDelivered" });
    expect(contactCheckOutcome(result("delivered", true)).key).toBe("notifications.contacts.testSimulated");
    expect(contactCheckOutcome(result("pending")).tone).toBe("info");
    expect(contactCheckOutcome(result("dead")).tone).toBe("error");
  });

  it("recognise this browser's device while it keeps its subscription", () => {
    const devices: PushDevice[] = [
      { id: "push_1", language: "en", created_at: 1 },
      { id: "push_2", language: "ka", created_at: 2 },
    ];
    const remembered = { endpoint: "https://fcm.googleapis.com/x", deviceId: "push_2" };
    expect(findThisDevice(devices, remembered, "https://fcm.googleapis.com/x")?.id).toBe("push_2");
    expect(findThisDevice(devices, remembered, "https://fcm.googleapis.com/other")).toBeNull();
    expect(findThisDevice(devices, remembered, null)).toBeNull();
    expect(findThisDevice(devices, null, "https://fcm.googleapis.com/x")).toBeNull();
    expect(findThisDevice([], remembered, "https://fcm.googleapis.com/x")).toBeNull();
  });
});

import { describe, expect, it } from "vitest";

import {
  clearSegment,
  draftFromValue,
  draftValue,
  EMPTY_DRAFT,
  hourText,
  periodOfDraft,
  segmentsOf,
  stepSegment,
  typeKey,
  typeText,
  withPeriod,
  type TimeEditing,
} from "./timeSegments";

const PERIODS = { am: "AM", pm: "PM" };
const start = (value = ""): TimeEditing => ({ draft: draftFromValue(value), segment: "hour", buffer: "" });

describe("typing into a 24-hour field", () => {
  it.each([
    ["0830", "08:30"],
    ["830", "08:30"],
    ["2030", "20:30"],
    ["1745", "17:45"],
    ["8:5", "08:05"],
    ["9:07", "09:07"],
    ["250", "02:50"],
    ["2500", "02:00"],
    ["0", ""],
  ])("%s gives %s", (typed, value) => {
    expect(draftValue(typeText(start(), typed, "h23", PERIODS).draft)).toBe(value);
  });

  it("moves to the minutes once the hour is whole", () => {
    expect(typeKey(start(), "9", "h23", PERIODS).segment).toBe("minute");
    const pending = typeKey(start(), "1", "h23", PERIODS);
    expect(pending).toMatchObject({ segment: "hour", buffer: "1" });
    expect(pending.draft.hour).toBe(1);
    expect(typeKey(pending, "2", "h23", PERIODS)).toMatchObject({ segment: "minute", buffer: "" });
    expect(typeKey(start(), ":", "h23", PERIODS).segment).toBe("minute");
  });

  it("stays on the minutes after the last digit and ignores letters", () => {
    const done = typeText(start(), "0830", "h23", PERIODS);
    expect(done.segment).toBe("minute");
    expect(typeKey(done, "p", "h23", PERIODS)).toEqual(done);
    expect(typeKey({ ...done, segment: "period" }, "5", "h23", PERIODS).draft).toEqual(done.draft);
  });
});

describe("typing into a 12-hour field", () => {
  it("reads afternoon hours typed on a 24-hour clock", () => {
    const evening = typeText(start(), "2030", "h12", PERIODS);
    expect(draftValue(evening.draft)).toBe("20:30");
    expect(evening.segment).toBe("period");
    expect(hourText(evening.draft.hour ?? 0, "h12")).toBe("08");
  });

  it("keeps the half of the day already chosen for hours up to 12", () => {
    const night = start("22:00");
    expect(draftValue(typeText(night, "0915", "h12", PERIODS).draft)).toBe("21:15");
    expect(draftValue(typeText(start(), "0915", "h12", PERIODS).draft)).toBe("09:15");
    expect(draftValue(typeText(start(), "0000", "h12", PERIODS).draft)).toBe("00:00");
  });

  it("chooses AM or PM by letter from any segment", () => {
    expect(draftValue(typeText(start(), "830p", "h12", PERIODS).draft)).toBe("20:30");
    const evening = typeText(start(), "2030", "h12", PERIODS);
    expect(draftValue(typeKey(evening, "a", "h12", PERIODS).draft)).toBe("08:30");
    expect(draftValue(typeKey(evening, "x", "h12", PERIODS).draft)).toBe("20:30");
    // A locale's own first letter works too.
    const own = { am: "ص", pm: "م" };
    expect(draftValue(typeKey(evening, "ص", "h12", own).draft)).toBe("08:30");
    expect(typeKey(start(), "p", "h12", PERIODS).draft.period).toBe("pm");
  });

  it("shows midnight and noon as 12", () => {
    expect(hourText(0, "h12")).toBe("12");
    expect(hourText(12, "h12")).toBe("12");
    expect(hourText(0, "h23")).toBe("00");
    expect(segmentsOf("h12")).toEqual(["hour", "minute", "period"]);
    expect(segmentsOf("h23")).toEqual(["hour", "minute"]);
  });
});

describe("arrows", () => {
  const options = { step: 15, fallback: 9 * 60 };

  it("start an empty field from the fallback", () => {
    expect(draftValue(stepSegment(EMPTY_DRAFT, "minute", 1, options))).toBe("09:00");
    expect(draftValue(stepSegment(EMPTY_DRAFT, "hour", -1, options))).toBe("09:00");
  });

  it("step the minutes along their grid and carry into the hours", () => {
    expect(draftValue(stepSegment(draftFromValue("08:10"), "minute", 1, options))).toBe("08:15");
    expect(draftValue(stepSegment(draftFromValue("08:45"), "minute", 1, options))).toBe("09:00");
    expect(draftValue(stepSegment(draftFromValue("00:00"), "minute", -1, { ...options, step: 30 }))).toBe("23:30");
    expect(stepSegment({ hour: null, minute: 50, period: null }, "minute", 1, options).minute).toBe(0);
    expect(stepSegment({ hour: 8, minute: null, period: null }, "minute", 1, options).minute).toBe(0);
  });

  it("step the hours by one around the day and flip AM and PM", () => {
    expect(draftValue(stepSegment(draftFromValue("23:30"), "hour", 1, options))).toBe("00:30");
    expect(draftValue(stepSegment(draftFromValue("00:30"), "hour", -1, options))).toBe("23:30");
    expect(stepSegment({ hour: null, minute: 5, period: null }, "hour", 1, options).hour).toBe(9);
    expect(draftValue(stepSegment(draftFromValue("08:30"), "period", 1, options))).toBe("20:30");
    expect(stepSegment(EMPTY_DRAFT, "period", 1, options).period).toBe("pm");
  });
});

describe("clearing", () => {
  it("empties a segment and keeps the half of the day", () => {
    const cleared = clearSegment(draftFromValue("20:30"), "hour");
    expect(cleared).toEqual({ hour: null, minute: 30, period: "pm" });
    expect(draftValue(cleared)).toBe("");
    expect(periodOfDraft(cleared)).toBe("pm");
    expect(clearSegment(draftFromValue("20:30"), "minute").minute).toBeNull();
    expect(clearSegment(draftFromValue("20:30"), "period")).toEqual(draftFromValue("20:30"));
    expect(withPeriod({ hour: null, minute: null, period: null }, "am").period).toBe("am");
  });
});

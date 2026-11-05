import { describe, expect, it } from "vitest";

import { dayPeriods, hourCycle } from "./intl/localeCalendar";
import { isTwelveHour, minutesOf, parseTypedTime, stepTime, timeText, timeValue } from "./timeInput";

describe("the clock of a locale", () => {
  it("is 24-hour in Russian, Georgian and Hebrew, 12-hour in English", () => {
    expect(hourCycle("ru")).toBe("h23");
    expect(hourCycle("ka")).toBe("h23");
    expect(hourCycle("ka-GE")).toBe("h23");
    expect(hourCycle("he")).toBe("h23");
    expect(hourCycle("en")).toBe("h12");
    expect(hourCycle("en-GB")).toBe("h23");
    expect(isTwelveHour("en")).toBe(true);
    expect(isTwelveHour("ru")).toBe(false);
  });

  it("names the halves of a 12-hour day", () => {
    expect(dayPeriods("en")).toEqual({ am: "AM", pm: "PM" });
    // A locale the platform cannot name falls back to AM/PM.
    expect(dayPeriods("zz-invalid-tag-!")).toEqual({ am: "AM", pm: "PM" });
  });
});

describe("timeText", () => {
  it("writes 08:00 in Russian and Georgian, never AM", () => {
    expect(timeText(8 * 60, "ru")).toBe("08:00");
    expect(timeText(8 * 60, "ka")).toBe("08:00");
    expect(timeText(22 * 60, "ru")).toBe("22:00");
    expect(timeText(22 * 60, "ka")).toBe("22:00");
    expect(timeText(8 * 60, "ru")).not.toMatch(/AM|PM/);
  });

  it("writes the English clock with AM and PM", () => {
    expect(timeText(8 * 60, "en")).toMatch(/^8:00\sAM$/);
    expect(timeText(22 * 60 + 30, "en")).toMatch(/^10:30\sPM$/);
    expect(timeText(0, "en")).toMatch(/^12:00\sAM$/);
  });

  it("writes Hebrew on a 24-hour clock", () => {
    expect(timeText(8 * 60, "he")).toBe("08:00");
    expect(timeText(20 * 60 + 5, "he")).toBe("20:05");
  });
});

describe("parseTypedTime", () => {
  it.each([
    ["0830", 510],
    ["830", 510],
    ["8:30", 510],
    ["08.30", 510],
    ["8 30", 510],
    ["8h30", 510],
    ["8", 480],
    ["20", 1200],
    ["2030", 1230],
    ["23:59", 1439],
    ["00:00", 0],
  ])("reads %s on a 24-hour clock in every language", (typed, minutes) => {
    for (const locale of ["ru", "ka", "en", "he"]) {
      expect(parseTypedTime(typed, locale)).toBe(minutes);
    }
  });

  it("reads a day period after the time", () => {
    expect(parseTypedTime("8:30 pm", "en")).toBe(20 * 60 + 30);
    expect(parseTypedTime("8:30PM", "en")).toBe(20 * 60 + 30);
    expect(parseTypedTime("830p", "en")).toBe(20 * 60 + 30);
    expect(parseTypedTime("8 a.m.", "en")).toBe(8 * 60);
    expect(parseTypedTime("12:15 am", "en")).toBe(15);
    expect(parseTypedTime("12:15 pm", "en")).toBe(12 * 60 + 15);
    // Typed in Russian as well: AM/PM are understood everywhere.
    expect(parseTypedTime("8:30 PM", "ru")).toBe(20 * 60 + 30);
  });

  it.each(["", "abc", "24:00", "8:60", "12345", "13 pm", "0 am", "8:30 xm", "8:3"])("refuses %j", (typed) => {
    expect(parseTypedTime(typed, "en")).toBeNull();
  });
});

describe("values and steps", () => {
  it("converts between HH:MM and minutes", () => {
    expect(minutesOf("08:30")).toBe(510);
    expect(minutesOf("8:30")).toBeNull();
    expect(minutesOf("24:00")).toBeNull();
    expect(timeValue(510)).toBe("08:30");
    expect(timeValue(1440)).toBe("00:00");
    expect(timeValue(-15)).toBe("23:45");
  });

  it("steps to the next multiple of the step and wraps around midnight", () => {
    expect(stepTime(8 * 60 + 10, 1, 15)).toBe(8 * 60 + 15);
    expect(stepTime(8 * 60 + 10, -1, 15)).toBe(8 * 60);
    expect(stepTime(8 * 60, 1, 30)).toBe(8 * 60 + 30);
    expect(stepTime(8 * 60, -1, 30)).toBe(7 * 60 + 30);
    expect(stepTime(23 * 60 + 45, 1, 15)).toBe(0);
    expect(stepTime(0, -1, 15)).toBe(23 * 60 + 45);
    expect(stepTime(7, 1, 0)).toBe(8);
  });
});

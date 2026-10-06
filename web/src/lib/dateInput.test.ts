import { describe, expect, it } from "vitest";

import {
  addDaysIso,
  addMonthsIso,
  clampIso,
  dateText,
  deviceToday,
  isIsoDate,
  isWithin,
  monthTitle,
  monthWeeks,
  parseTypedDate,
  weekColumns,
} from "./dateInput";
import { dateFieldOrder, firstDayOfWeek } from "./intl/localeCalendar";

const TODAY = "2026-10-06";

describe("the calendar of a locale", () => {
  it("starts the week on Monday in Russian and Georgian, on Sunday in English and Hebrew", () => {
    expect(firstDayOfWeek("ru")).toBe(1);
    expect(firstDayOfWeek("ka")).toBe(1);
    expect(firstDayOfWeek("en")).toBe(7);
    expect(firstDayOfWeek("he")).toBe(7);
    expect(firstDayOfWeek("en-GB")).toBe(1);
    expect(firstDayOfWeek("ar")).toBe(6);
    expect(firstDayOfWeek("dv")).toBe(5);
    expect(firstDayOfWeek("de_AT")).toBe(1);
    expect(weekColumns("ru")).toEqual([1, 2, 3, 4, 5, 6, 7]);
    expect(weekColumns("en")).toEqual([7, 1, 2, 3, 4, 5, 6]);
  });

  it("orders typed numbers as the locale writes them", () => {
    expect(dateFieldOrder("en")).toEqual(["month", "day", "year"]);
    expect(dateFieldOrder("ru")).toEqual(["day", "month", "year"]);
    expect(dateFieldOrder("ka")).toEqual(["day", "month", "year"]);
    expect(dateFieldOrder("he")).toEqual(["day", "month", "year"]);
  });
});

describe("dateText", () => {
  it("writes the date in the cabinet's language, never mm/dd/yyyy", () => {
    expect(dateText(TODAY, "ru")).toBe("6 окт. 2026 г.");
    expect(dateText(TODAY, "ka")).toBe("6 ოქტ. 2026");
    expect(dateText(TODAY, "en")).toBe("Oct 6, 2026");
    expect(dateText(TODAY, "he")).toMatch(/2026/);
    expect(dateText("2026-02-31", "en")).toBe("");
    expect(dateText(TODAY, "ru", "full")).toBe("вторник, 6 октября 2026 г.");
  });

  it("titles a month", () => {
    expect(monthTitle(2026, 10, "ru")).toBe("Октябрь 2026 г.");
    expect(monthTitle(2026, 10, "ka")).toBe("ოქტომბერი, 2026");
    expect(monthTitle(2026, 10, "en")).toBe("October 2026");
  });
});

describe("parseTypedDate", () => {
  it("reads ISO in every language", () => {
    for (const locale of ["ru", "ka", "en", "he"]) {
      expect(parseTypedDate("2026-10-06", locale, TODAY)).toBe(TODAY);
      expect(parseTypedDate("2026-2-30", locale, TODAY)).toBeNull();
    }
  });

  it("reads numbers in the locale's order", () => {
    expect(parseTypedDate("06.10.2026", "ru", TODAY)).toBe(TODAY);
    expect(parseTypedDate("6.10.26", "ka", TODAY)).toBe(TODAY);
    expect(parseTypedDate("06/10/2026", "he", TODAY)).toBe(TODAY);
    expect(parseTypedDate("10/06/2026", "en", TODAY)).toBe(TODAY);
    expect(parseTypedDate("6.10", "ru", TODAY)).toBe(TODAY);
    expect(parseTypedDate("10/6", "en", TODAY)).toBe(TODAY);
  });

  it("reads what the field itself shows, and month names", () => {
    for (const locale of ["ru", "ka", "en", "he"]) {
      expect(parseTypedDate(dateText(TODAY, locale), locale, TODAY)).toBe(TODAY);
      expect(parseTypedDate(dateText("2027-05-31", locale, "long"), locale, TODAY)).toBe("2027-05-31");
    }
    expect(parseTypedDate("6 окт 2026", "ru", TODAY)).toBe(TODAY);
    expect(parseTypedDate("1 май", "ru", TODAY)).toBe("2026-05-01");
    expect(parseTypedDate("Oct 6", "ru", TODAY)).toBe(TODAY);
    expect(parseTypedDate("6 ოქტომბერი 2026", "ka", TODAY)).toBe(TODAY);
  });

  it.each(["", "завтра", "32.10.2026", "6.13.2026", "6", "1.2.3.4", "123456", "6 окт ноя", "6 7 окт", "окт"])("refuses %j", (typed) => {
    expect(parseTypedDate(typed, "ru", TODAY)).toBeNull();
  });
});

describe("calendar arithmetic", () => {
  it("adds days and months, keeping to real days", () => {
    expect(addDaysIso("2026-02-28", 1)).toBe("2026-03-01");
    expect(addDaysIso("2026-01-01", -1)).toBe("2025-12-31");
    expect(addMonthsIso("2028-01-31", 1)).toBe("2028-02-29");
    expect(addMonthsIso("2026-01-15", -1)).toBe("2025-12-15");
    expect(addMonthsIso("2026-12-15", 1)).toBe("2027-01-15");
    expect(addDaysIso("nope", 1)).toBe("nope");
    expect(addMonthsIso("nope", 1)).toBe("nope");
  });

  it("checks and clamps bounds", () => {
    expect(isIsoDate(TODAY)).toBe(true);
    expect(isIsoDate("2026-1-5")).toBe(false);
    expect(isIsoDate("2026-02-30")).toBe(false);
    expect(clampIso("2026-01-01", TODAY, null)).toBe(TODAY);
    expect(clampIso("2027-01-01", null, TODAY)).toBe(TODAY);
    expect(clampIso("2026-10-07", "", "")).toBe("2026-10-07");
    expect(isWithin("2026-10-07", TODAY, "2026-10-31")).toBe(true);
    expect(isWithin("2026-11-01", TODAY, "2026-10-31")).toBe(false);
    expect(deviceToday(new Date(2026, 9, 6, 23, 30))).toBe(TODAY);
  });

  it("lays a month out in weeks from the first day of the week", () => {
    // 1 October 2026 is a Thursday.
    const mondayFirst = monthWeeks(2026, 10, 1);
    expect(mondayFirst[0]).toEqual([null, null, null, "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04"]);
    expect(mondayFirst).toHaveLength(5);
    const sundayFirst = monthWeeks(2026, 10, 7);
    expect(sundayFirst[0]?.slice(0, 5)).toEqual([null, null, null, null, "2026-10-01"]);
    expect(sundayFirst.at(-1)?.filter(Boolean).at(-1)).toBe("2026-10-31");
    // February 2026 starts on a Sunday: a full first row when weeks start on Sunday.
    expect(monthWeeks(2026, 2, 7)[0]?.[0]).toBe("2026-02-01");
    expect(monthWeeks(2026, 2, 7)).toHaveLength(4);
  });
});

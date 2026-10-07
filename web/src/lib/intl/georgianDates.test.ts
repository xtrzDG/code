import { describe, expect, it } from "vitest";

import { dateTimeFormat } from "./formatters";
import { georgianDateFormat } from "./georgianDates";

// Node ships full ICU (`npm run check:intl`): its Georgian is the reference.
const native = (options: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat("ka", options);

const ZONES = ["UTC", "Asia/Tbilisi", "America/New_York"];

/** Every month and weekday, midnight, morning and late evening, a leap day and a two-digit day. */
const INSTANTS = [
  ...Array.from({ length: 12 }, (_, month) => new Date(Date.UTC(2026, month, 1 + month * 2, (month * 5) % 24, month * 4, month))),
  new Date(Date.UTC(2028, 1, 29, 0, 0, 0)),
  new Date(Date.UTC(2026, 9, 6, 23, 59, 59)),
  new Date(Date.UTC(1999, 11, 31, 9, 3, 7)),
];

/** The option sets the cabinet formats with, and their neighbours. */
const OPTION_SETS: Intl.DateTimeFormatOptions[] = [
  {},
  { dateStyle: "full" },
  { dateStyle: "long" },
  { dateStyle: "medium" },
  { dateStyle: "short" },
  { timeStyle: "short" },
  { timeStyle: "medium" },
  { dateStyle: "medium", timeStyle: "short" },
  { dateStyle: "full", timeStyle: "short" },
  { dateStyle: "long", timeStyle: "medium" },
  { weekday: "long" },
  { weekday: "short" },
  { day: "numeric", month: "short" },
  { day: "numeric", month: "long" },
  { day: "2-digit", month: "long", weekday: "long" },
  { weekday: "short", day: "numeric", month: "short" },
  { weekday: "long", day: "numeric", month: "long" },
  { weekday: "long", day: "numeric", month: "long", year: "numeric" },
  { weekday: "short", day: "numeric", month: "short", year: "numeric" },
  { day: "numeric", month: "long", year: "numeric" },
  { day: "2-digit", month: "short", year: "numeric" },
  { day: "numeric", month: "short", year: "2-digit" },
  { month: "long" },
  { month: "short", year: "numeric" },
  { month: "long", year: "numeric" },
  { month: "numeric" },
  { month: "2-digit" },
  { day: "numeric", month: "numeric" },
  { day: "2-digit", month: "2-digit" },
  { day: "numeric", month: "2-digit" },
  { day: "numeric", month: "numeric", year: "numeric" },
  { day: "2-digit", month: "2-digit", year: "numeric" },
  { day: "numeric", month: "numeric", year: "2-digit" },
  { month: "numeric", year: "numeric" },
  { weekday: "long", day: "numeric", month: "numeric" },
  { weekday: "short", day: "numeric", month: "numeric", year: "numeric" },
  { day: "numeric" },
  { day: "2-digit" },
  { year: "numeric" },
  { year: "2-digit" },
  { hour: "numeric" },
  { hour: "numeric", minute: "2-digit" },
  { hour: "2-digit", minute: "2-digit" },
  { hour: "numeric", minute: "2-digit", second: "2-digit" },
  { hour: "numeric", minute: "2-digit", hour12: false },
  { hour: "numeric", minute: "2-digit", hourCycle: "h23" },
  { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" },
  { weekday: "long", day: "numeric", month: "long", year: "numeric", hour: "numeric", minute: "2-digit" },
];

describe("Georgian dates", () => {
  it("are written as Node's ICU writes them", () => {
    for (const options of OPTION_SETS) {
      for (const timeZone of ZONES) {
        const ours = georgianDateFormat({ ...options, timeZone });
        expect(ours, JSON.stringify(options)).not.toBeNull();
        const reference = native({ ...options, timeZone });
        for (const instant of INSTANTS) {
          expect(ours!.format(instant), `${JSON.stringify(options)} ${timeZone} ${instant.toISOString()}`).toBe(
            reference.format(instant),
          );
        }
      }
    }
  });

  it("leave time zone names, 12-hour clocks and odd field sets to the platform", () => {
    for (const options of [
      { timeStyle: "long" },
      { timeStyle: "full" },
      { dateStyle: "medium", weekday: "long" },
      { dateStyle: "medium", hour: "numeric" },
      { timeZoneName: "short", hour: "numeric" },
      { hour: "numeric", hour12: true },
      { hour: "numeric", hourCycle: "h11" },
      { weekday: "narrow" },
      { month: "narrow" },
      { weekday: "long", month: "long" },
      { weekday: "short", day: "numeric" },
      { weekday: "short", year: "numeric" },
      { day: "numeric", year: "numeric" },
      { minute: "2-digit" },
      { hour: "numeric", second: "2-digit" },
    ] as Intl.DateTimeFormatOptions[]) {
      expect(georgianDateFormat(options), JSON.stringify(options)).toBeNull();
    }
  });

  it("write a range of days with the shared year once", () => {
    const format = georgianDateFormat({ dateStyle: "medium", timeZone: "UTC" })!;
    const day = (month: number, date: number, year = 2026) => new Date(Date.UTC(year, month, date));
    expect(format.formatRange(day(8, 2), day(9, 1))).toBe("2 სექ. – 1 ოქტ. 2026");
    expect(format.formatRange(day(9, 6), day(9, 20))).toBe("6–20 ოქტ. 2026");
    expect(format.formatRange(day(11, 30), day(0, 3, 2027))).toBe("30 დეკ. 2026 – 3 იან. 2027");
    expect(format.formatRange(day(9, 6), new Date(Date.UTC(2026, 9, 6, 18)))).toBe("6 ოქტ. 2026");
    const long = georgianDateFormat({ dateStyle: "long", timeZone: "UTC" })!;
    expect(long.formatRange(day(8, 2), day(9, 1))).toBe("2 სექტემბერი, 2026 – 1 ოქტომბერი, 2026");
  });

  it("fail like the platform on an invalid date", () => {
    expect(() => georgianDateFormat()!.format(new Date(Number.NaN))).toThrow(RangeError);
  });
});

describe("the date factory", () => {
  const instant = new Date(Date.UTC(2026, 9, 16, 8, 0));

  it("writes Georgian for any Georgian tag and keeps the time zone", () => {
    for (const locale of ["ka", "ka-GE", "KA_ge"]) {
      expect(dateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Tbilisi" }).format(instant)).toBe(
        "16 ოქტ. 2026, 12:00",
      );
    }
  });

  it("asks the platform for other languages and for options Georgian tables lack", () => {
    const options: Intl.DateTimeFormatOptions = { dateStyle: "medium", timeZone: "UTC" };
    expect(dateTimeFormat("ru", options).format(instant)).toBe(new Intl.DateTimeFormat("ru", options).format(instant));
    const end = new Date(Date.UTC(2026, 9, 20));
    expect(dateTimeFormat("en", options).formatRange(instant, end)).toBe(
      new Intl.DateTimeFormat("en", options).formatRange(instant, end),
    );
    const zoned: Intl.DateTimeFormatOptions = { timeStyle: "full", timeZone: "UTC" };
    expect(dateTimeFormat("ka", zoned).format(instant)).toBe(native(zoned).format(instant));
    expect(dateTimeFormat("kab", options).format(instant)).toBe(new Intl.DateTimeFormat("kab", options).format(instant));
  });
});

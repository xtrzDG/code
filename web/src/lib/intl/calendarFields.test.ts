import { describe, expect, it } from "vitest";

import { calendarFieldFormat, calendarParts, isKnownTimeZone, systemTimeZone } from "./calendarFields";

describe("calendar fields of an instant in a zone", () => {
  const at = new Date(Date.UTC(2026, 9, 4, 22, 30));

  it("reads the local day in the zone, not in the zone of the machine", () => {
    expect(calendarParts(at, "Asia/Tbilisi", { year: "numeric", month: "2-digit", day: "2-digit" })).toMatchObject({
      year: "2026",
      month: "10",
      day: "05",
    });
    expect(calendarParts(at, "America/New_York", { year: "numeric", month: "2-digit", day: "2-digit" }, "en-CA")).toMatchObject({
      year: "2026",
      month: "10",
      day: "04",
    });
  });

  it("caches one formatter per locale and option set", () => {
    const first = calendarFieldFormat("en-US", { timeZone: "UTC", hour: "2-digit" });
    expect(calendarFieldFormat("en-US", { timeZone: "UTC", hour: "2-digit" })).toBe(first);
    expect(calendarFieldFormat("en-CA", { timeZone: "UTC", hour: "2-digit" })).not.toBe(first);
  });

  it("knows real zones and refuses made-up or oversized ones", () => {
    expect(isKnownTimeZone("Asia/Tbilisi")).toBe(true);
    expect(isKnownTimeZone("UTC")).toBe(true);
    expect(isKnownTimeZone("Mars/Olympus_Mons")).toBe(false);
    expect(isKnownTimeZone("")).toBe(false);
    expect(isKnownTimeZone(`Europe/${"x".repeat(80)}`)).toBe(false);
  });

  it("names the zone of the machine running the code", () => {
    const zone = systemTimeZone();
    expect(zone === null || isKnownTimeZone(zone)).toBe(true);
  });
});

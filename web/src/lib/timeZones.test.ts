import { describe, expect, it } from "vitest";

import { formatUtcOffset, sortZones, timeZoneLabel, utcOffsetMinutes, zoneCity } from "./timeZones";

const WINTER = new Date(Date.UTC(2026, 0, 15, 12));
const SUMMER = new Date(Date.UTC(2026, 6, 15, 12));

describe("time zone labels", () => {
  it("name the city in the interface language with the offset in force", () => {
    expect(timeZoneLabel("Asia/Tbilisi", "ru", SUMMER)).toBe("Тбилиси (UTC+4)");
    expect(timeZoneLabel("Asia/Tbilisi", "ka", SUMMER)).toBe("თბილისი (UTC+4)");
    expect(timeZoneLabel("Asia/Tbilisi", "en", SUMMER)).toBe("Tbilisi (UTC+4)");
  });

  it("follow summer time", () => {
    expect(timeZoneLabel("Europe/Berlin", "ru", WINTER)).toBe("Берлин (UTC+1)");
    expect(timeZoneLabel("Europe/Berlin", "ru", SUMMER)).toBe("Берлин (UTC+2)");
    expect(timeZoneLabel("America/New_York", "en", SUMMER)).toBe("New York (UTC−4)");
  });

  it("write half hours and UTC itself", () => {
    expect(timeZoneLabel("Asia/Kolkata", "en", SUMMER)).toBe("Kolkata (UTC+5:30)");
    expect(formatUtcOffset(0)).toBe("UTC");
    expect(formatUtcOffset(345)).toBe("UTC+5:45");
    expect(formatUtcOffset(-210)).toBe("UTC−3:30");
  });

  it("use CLDR's spelling where it differs from the zone name", () => {
    expect(zoneCity("Europe/Kiev", "en")).toBe("Kyiv");
    expect(zoneCity("Europe/Kiev", "ru")).toBe("Киев");
    expect(zoneCity("America/Argentina/Buenos_Aires", "en")).toBe("Buenos Aires");
  });

  it("show just the city for a zone the browser does not know", () => {
    expect(utcOffsetMinutes("Mars/Olympus_Mons", SUMMER)).toBeNull();
    expect(timeZoneLabel("Mars/Olympus_Mons", "en", SUMMER)).toBe("Olympus Mons");
  });

  it("sort zones from west to east, then by city", () => {
    expect(sortZones(["Asia/Tbilisi", "America/New_York", "Europe/Berlin", "Europe/Paris"], "en", SUMMER)).toEqual([
      "America/New_York",
      "Europe/Berlin",
      "Europe/Paris",
      "Asia/Tbilisi",
    ]);
  });
});

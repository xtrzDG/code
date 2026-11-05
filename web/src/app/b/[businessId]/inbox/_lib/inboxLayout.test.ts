import { describe, expect, it } from "vitest";

import { rowAge } from "./rowAge";
import {
  clampListWidth,
  DEFAULT_INBOX_DENSITY,
  listColumns,
  MAX_LIST_WIDTH,
  MIN_LIST_WIDTH,
  parseDensity,
  parseListWidth,
  widthAfterKey,
} from "./inboxLayout";

describe("row density", () => {
  it("is comfortable unless the person chose compact", () => {
    expect(DEFAULT_INBOX_DENSITY).toBe("comfortable");
    expect(parseDensity("compact")).toBe("compact");
    expect(parseDensity("comfortable")).toBe("comfortable");
    expect(parseDensity(null)).toBe("comfortable");
    expect(parseDensity("tiny")).toBe("comfortable");
  });
});

describe("the list column's width", () => {
  it("stays within 320–520 px in whole pixels", () => {
    expect(clampListWidth(100)).toBe(MIN_LIST_WIDTH);
    expect(clampListWidth(900)).toBe(MAX_LIST_WIDTH);
    expect(clampListWidth(401.6)).toBe(402);
  });

  it("reads a remembered width, and the responsive default for nothing or nonsense", () => {
    expect(parseListWidth("440")).toBe(440);
    expect(parseListWidth("999")).toBe(MAX_LIST_WIDTH);
    expect(parseListWidth(null)).toBeNull();
    expect(parseListWidth("wide")).toBeNull();
    expect(parseListWidth("4400")).toBeNull();
  });

  it("moves 16 px per arrow key, to the ends with Home and End, and ignores other keys", () => {
    expect(widthAfterKey("ArrowRight", 400)).toBe(416);
    expect(widthAfterKey("ArrowLeft", 400)).toBe(384);
    expect(widthAfterKey("ArrowLeft", 330)).toBe(MIN_LIST_WIDTH);
    expect(widthAfterKey("Home", 400)).toBe(MIN_LIST_WIDTH);
    expect(widthAfterKey("End", 400)).toBe(MAX_LIST_WIDTH);
    expect(widthAfterKey("Enter", 400)).toBeNull();
  });

  it("leaves the conversation at least 440 px beside it", () => {
    expect(listColumns(480)).toBe("minmax(320px, min(480px, calc(100% - 460px))) minmax(0, 1fr)");
    expect(listColumns(9000)).toContain("min(520px,");
  });
});

describe("the age of a row's last message", () => {
  const now = Date.UTC(2026, 9, 6, 12, 0, 0);
  const ago = (ms: number) => (now - ms) * 1000;

  it("reads now, minutes, hours and days", () => {
    expect(rowAge(ago(20_000), now)).toEqual({ unit: "now" });
    expect(rowAge(ago(5 * 60_000), now)).toEqual({ unit: "minutes", count: 5 });
    expect(rowAge(ago(3 * 3_600_000 + 59_000), now)).toEqual({ unit: "hours", count: 3 });
    expect(rowAge(ago(2 * 86_400_000), now)).toEqual({ unit: "days", count: 2 });
  });

  it("gives the date from a week on, and treats a clock ahead of the server as now", () => {
    expect(rowAge(ago(7 * 86_400_000), now)).toBeNull();
    expect(rowAge(ago(-30_000), now)).toEqual({ unit: "now" });
  });
});

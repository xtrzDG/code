import { describe, expect, it } from "vitest";

import { entryDay, newestFirst, newestKey, unreadKeys, type ChangelogEntry } from "./changelog";

const text = { title: "T", body: ["B"] };
const entry = (key: string): ChangelogEntry => ({ key, texts: { en: text, ru: text, ka: text } });
const ENTRIES = [entry("2026-09-13-value"), entry("2026-10-04-help-center"), entry("2026-09-27-profile")];

describe("the changelog", () => {
  it("lists the newest entry first", () => {
    expect(newestFirst(ENTRIES).map((item) => item.key)).toEqual([
      "2026-10-04-help-center",
      "2026-09-27-profile",
      "2026-09-13-value",
    ]);
    expect(newestFirst([entry("2026-01-01"), entry("2026-01-01")])).toHaveLength(2);
    expect(newestKey(ENTRIES)).toBe("2026-10-04-help-center");
    expect(newestKey([])).toBeNull();
  });

  it("counts the entries after the last one read", () => {
    expect(unreadKeys(ENTRIES, "2026-09-13-value")).toEqual(["2026-10-04-help-center", "2026-09-27-profile"]);
    expect(unreadKeys(ENTRIES, "2026-10-04-help-center")).toEqual([]);
  });

  it("shows only the newest entry as new to someone who never read any", () => {
    expect(unreadKeys(ENTRIES, null)).toEqual(["2026-10-04-help-center"]);
    expect(unreadKeys([], undefined)).toEqual([]);
  });

  it("reads the day from the key", () => {
    expect(entryDay(entry("2026-10-04-help-center"))?.toISOString()).toBe("2026-10-04T00:00:00.000Z");
    expect(entryDay(entry("2026-02-30-nope"))).toBeNull();
    expect(entryDay(entry("help-center"))).toBeNull();
  });
});

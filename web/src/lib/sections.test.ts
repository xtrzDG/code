import { describe, expect, it } from "vitest";

import { BUSINESS_PAGES } from "./navigation";
import {
  BUSINESS_SECTIONS,
  PAGE_DESCRIPTIONS,
  SECTION_PAGES,
  canOpenPage,
  listedPages,
  pageLabel,
  pageTitleKeys,
  sectionOf,
  visiblePages,
  visibleSections,
} from "./sections";

describe("the five sections", () => {
  it("list every page exactly once, each in the section of its address", () => {
    expect([...listedPages()].sort()).toEqual([...BUSINESS_PAGES].sort());
    for (const section of BUSINESS_SECTIONS) {
      expect(SECTION_PAGES[section][0]?.page).toBe(section);
      for (const entry of SECTION_PAGES[section]) {
        expect(sectionOf(entry.page)).toBe(section);
      }
    }
  });

  it("show owners everything", () => {
    expect(visibleSections("owner")).toEqual(["overview", "inbox", "bookings", "assistant", "settings"]);
    expect(BUSINESS_PAGES.every((page) => canOpenPage(page, "owner"))).toBe(true);
  });

  it("show staff the overview, the inbox, bookings, the test chat and their notifications", () => {
    expect(visibleSections("staff")).toEqual(["overview", "inbox", "bookings", "assistant", "settings"]);
    expect(visiblePages("settings", "staff").map((entry) => entry.page)).toEqual(["settings/notifications"]);
    expect(visiblePages("assistant", "staff").map((entry) => entry.page)).toEqual(["assistant"]);
    expect(visiblePages("overview", "staff").map((entry) => entry.page)).toEqual(["overview"]);
    expect(canOpenPage("overview/reports", "staff")).toBe(false);
    expect(visiblePages("inbox", "staff").map((entry) => entry.page)).toEqual(["inbox"]);
    expect(canOpenPage("settings/billing", "staff")).toBe(false);
    expect(canOpenPage("settings/calls", "staff")).toBe(false);
    expect(canOpenPage("assistant/knowledge", "staff")).toBe(false);
    expect(canOpenPage("inbox", "staff")).toBe(true);
    expect(canOpenPage("settings/quick-replies", "staff")).toBe(false);
  });

  it("keep versions and autotests under Advanced", () => {
    const advanced = SECTION_PAGES.assistant.filter((entry) => entry.isAdvanced).map((entry) => entry.page);
    expect(advanced).toEqual(["assistant/versions"]);
  });

  it("name pages and their titles", () => {
    expect(pageLabel("bookings")).toBe("navigation.sections.bookings");
    expect(pageLabel("inbox")).toBe("navigation.sections.inbox");
    expect(pageLabel("settings/quick-replies")).toBe("navigation.pages.settingsQuickReplies");
    expect(pageTitleKeys("overview")).toEqual(["navigation.pages.overviewDashboard", "navigation.sections.overview"]);
    expect(pageTitleKeys("overview/reports")).toEqual(["navigation.pages.overviewReports", "navigation.sections.overview"]);
    expect(pageTitleKeys("settings/team")).toEqual(["navigation.pages.settingsTeam", "navigation.sections.settings"]);
    expect(pageTitleKeys("assistant")).toEqual(["navigation.pages.assistantTest", "navigation.sections.assistant"]);
    expect(pageTitleKeys("inbox")).toEqual(["navigation.sections.inbox"]);
    expect(PAGE_DESCRIPTIONS.inbox).toBe("navigation.descriptions.inbox");
  });

  it("refuses a page missing from the tables", () => {
    expect(() => canOpenPage("unknown" as never, "owner")).toThrow(/missing/);
  });
});

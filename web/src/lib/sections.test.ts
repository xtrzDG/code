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
    expect(visibleSections("owner")).toEqual(["overview", "messages", "bookings", "assistant", "settings"]);
    expect(BUSINESS_PAGES.every((page) => canOpenPage(page, "owner"))).toBe(true);
  });

  it("show staff the overview, messages, bookings and the test chat", () => {
    expect(visibleSections("staff")).toEqual(["overview", "messages", "bookings", "assistant"]);
    expect(visiblePages("assistant", "staff").map((entry) => entry.page)).toEqual(["assistant"]);
    expect(visiblePages("messages", "staff")).toHaveLength(3);
    expect(canOpenPage("settings/billing", "staff")).toBe(false);
    expect(canOpenPage("assistant/knowledge", "staff")).toBe(false);
    expect(canOpenPage("messages/leads", "staff")).toBe(true);
  });

  it("keep versions and autotests under Advanced", () => {
    const advanced = SECTION_PAGES.assistant.filter((entry) => entry.isAdvanced).map((entry) => entry.page);
    expect(advanced).toEqual(["assistant/versions"]);
  });

  it("name pages and their titles", () => {
    expect(pageLabel("bookings")).toBe("navigation.sections.bookings");
    expect(pageLabel("messages/handoffs")).toBe("navigation.pages.messagesHandoffs");
    expect(pageTitleKeys("overview")).toEqual(["navigation.sections.overview"]);
    expect(pageTitleKeys("settings/team")).toEqual(["navigation.pages.settingsTeam", "navigation.sections.settings"]);
    expect(pageTitleKeys("assistant")).toEqual(["navigation.pages.assistantTest", "navigation.sections.assistant"]);
    expect(PAGE_DESCRIPTIONS["messages/leads"]).toBe("pages.leads.description");
  });

  it("refuses a page missing from the tables", () => {
    expect(() => canOpenPage("unknown" as never, "owner")).toThrow(/missing/);
  });
});

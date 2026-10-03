import { describe, expect, it } from "vitest";

import {
  BUSINESS_PAGES,
  businessLocation,
  businessPath,
  isBusinessPage,
  isConversationPath,
  samePageIn,
  sectionFromPathname,
  setupPath,
} from "./navigation";

describe("business pages", () => {
  it("builds the address of a page, the overview by default", () => {
    expect(businessPath("biz_1")).toBe("/b/biz_1/overview");
    expect(businessPath("biz_1", "messages/handoffs")).toBe("/b/biz_1/messages/handoffs");
    expect(businessPath("a b/c", "settings")).toBe("/b/a%20b%2Fc/settings");
    expect(setupPath("biz_1")).toBe("/b/biz_1/setup");
    expect(setupPath("biz 1", "hours")).toBe("/b/biz%201/setup?step=hours");
  });

  it("knows its pages", () => {
    expect(isBusinessPage("assistant/knowledge")).toBe(true);
    expect(isBusinessPage("dashboard")).toBe(false);
    expect(isBusinessPage(undefined)).toBe(false);
    expect(new Set(BUSINESS_PAGES).size).toBe(BUSINESS_PAGES.length);
  });

  it("finds the most specific page of a path", () => {
    expect(businessLocation("/b/biz_1/overview")).toEqual({ businessId: "biz_1", page: "overview", isSetup: false });
    expect(businessLocation("/b/biz_1/messages")?.page).toBe("messages");
    expect(businessLocation("/b/biz_1/messages/conv_7")?.page).toBe("messages");
    expect(businessLocation("/b/biz_1/messages/handoffs")?.page).toBe("messages/handoffs");
    expect(businessLocation("/b/biz_1/assistant/knowledge/import")?.page).toBe("assistant/knowledge");
    expect(businessLocation("/b/biz_1/assistant/versions/ver_2")?.page).toBe("assistant/versions");
    expect(businessLocation("/b/biz_1/settings/team")?.page).toBe("settings/team");
    expect(businessLocation("/b/biz%201/settings")?.businessId).toBe("biz 1");
  });

  it("tells the setup flow and unknown places apart", () => {
    expect(businessLocation("/b/biz_1/setup")).toEqual({ businessId: "biz_1", page: null, isSetup: true });
    expect(businessLocation("/b/biz_1/onboarding")).toEqual({ businessId: "biz_1", page: null, isSetup: true });
    expect(businessLocation("/b/biz_1")).toEqual({ businessId: "biz_1", page: null, isSetup: false });
    expect(businessLocation("/b/biz_1/dashboard")?.page).toBeNull();
    expect(businessLocation("/businesses")).toBeNull();
    expect(businessLocation("/b/")).toBeNull();
    expect(businessLocation("/b/%E0%A4%A")).toBeNull();
  });

  it("names the section of a path", () => {
    expect(sectionFromPathname("/b/biz_1/bookings/booking_2")).toBe("bookings");
    expect(sectionFromPathname("/b/biz_1/assistant/channels")).toBe("assistant");
    expect(sectionFromPathname("/b/biz_1/onboarding")).toBeNull();
  });

  it("recognises an open conversation", () => {
    expect(isConversationPath("/b/biz_1/messages/conv_1")).toBe(true);
    expect(isConversationPath("/b/biz_1/messages")).toBe(false);
    expect(isConversationPath("/b/biz_1/messages/leads")).toBe(false);
    expect(isConversationPath("/b/biz_1/bookings/x")).toBe(false);
  });

  it("keeps the page when switching business", () => {
    expect(samePageIn("biz_2", "/b/biz_1/messages/conv_1")).toBe("/b/biz_2/messages");
    expect(samePageIn("biz_2", "/b/biz_1/settings/team")).toBe("/b/biz_2/settings/team");
    expect(samePageIn("biz_2", "/b/biz_1/onboarding")).toBe("/b/biz_2/overview");
  });
});

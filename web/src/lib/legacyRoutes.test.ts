import { describe, expect, it } from "vitest";

import { LEGACY_ROUTES, legacyDestination, legacyRedirects } from "./legacyRoutes";
import { isBusinessPage } from "./navigation";

describe("addresses from before the five sections", () => {
  it("lead to pages that exist", () => {
    for (const route of LEGACY_ROUTES) {
      expect(isBusinessPage(route.to), route.to).toBe(true);
      expect(isBusinessPage(route.from), route.from).toBe(false);
    }
  });

  it("become next.config redirects that keep deeper paths where they move along", () => {
    expect(legacyRedirects()).toContainEqual({
      source: "/b/:businessId/conversations/:rest*",
      destination: "/b/:businessId/messages/:rest*",
      permanent: false,
    });
    expect(legacyRedirects()).toContainEqual({
      source: "/b/:businessId/billing",
      destination: "/b/:businessId/settings/billing",
      permanent: false,
    });
    expect(legacyRedirects().every((redirect) => redirect.permanent === false)).toBe(true);
  });

  it("map every old section to its new place", () => {
    expect(legacyDestination("/b/biz_1/dashboard")).toBe("/b/biz_1/overview");
    expect(legacyDestination("/b/biz_1/conversations")).toBe("/b/biz_1/messages");
    expect(legacyDestination("/b/biz_1/conversations/conv_9")).toBe("/b/biz_1/messages/conv_9");
    expect(legacyDestination("/b/biz_1/handoffs")).toBe("/b/biz_1/messages/handoffs");
    expect(legacyDestination("/b/biz_1/leads")).toBe("/b/biz_1/messages/leads");
    expect(legacyDestination("/b/biz_1/knowledge/import")).toBe("/b/biz_1/assistant/knowledge/import");
    expect(legacyDestination("/b/biz_1/channels")).toBe("/b/biz_1/assistant/channels");
    expect(legacyDestination("/b/biz_1/billing")).toBe("/b/biz_1/settings/billing");
  });

  it("leave current and unknown addresses alone", () => {
    expect(legacyDestination("/b/biz_1/overview")).toBeNull();
    expect(legacyDestination("/b/biz_1/handoffs/x")).toBeNull();
    expect(legacyDestination("/b/biz_1")).toBeNull();
    expect(legacyDestination("/businesses")).toBeNull();
  });
});

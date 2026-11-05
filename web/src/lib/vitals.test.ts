import { describe, expect, it } from "vitest";

import { deviceClassOf, routeTemplate, vitalReport } from "./vitals";

describe("Web Vitals reports", () => {
  it("name pages by their route template, never by ids", () => {
    expect(routeTemplate("/b/business_0d99/inbox/conversation_12")).toBe("/b/[businessId]/inbox/[conversationId]");
    expect(routeTemplate("/b/business_0d99/assistant/versions/version_1")).toBe("/b/[businessId]/assistant/versions/[versionId]");
    expect(routeTemplate("/b/business_0d99/settings/team")).toBe("/b/[businessId]/settings/team");
    expect(routeTemplate("/admin/clients/business_1")).toBe("/admin/clients/[businessId]");
    expect(routeTemplate("/admin/metrics")).toBe("/admin/metrics");
    expect(routeTemplate("/n/token-abc")).toBe("/n/[token]");
    expect(routeTemplate("/businesses")).toBe("/businesses");
    expect(routeTemplate("/create/")).toBe("/create");
    expect(routeTemplate("/b/x/%D0%B0")).toBeNull();
  });

  it("class devices by the viewport width", () => {
    expect(deviceClassOf(390)).toBe("mobile");
    expect(deviceClassOf(800)).toBe("tablet");
    expect(deviceClassOf(1440)).toBe("desktop");
  });

  it("report LCP and INP in milliseconds and CLS in ten-thousandths", () => {
    expect(vitalReport({ name: "LCP", value: 1834.6 }, "/b/biz_1/overview", 390)).toEqual({
      kind: "web_vital",
      metric: "lcp",
      value: 1835,
      route: "/b/[businessId]/overview",
      device_class: "mobile",
    });
    expect(vitalReport({ name: "CLS", value: 0.0812 }, "/businesses", 1440)?.value).toBe(812);
    expect(vitalReport({ name: "INP", value: 9_999_999 }, "/businesses", 1440)?.value).toBe(600_000);
  });

  it("leave out other vitals and pages without a session", () => {
    expect(vitalReport({ name: "TTFB", value: 100 }, "/businesses", 1440)).toBeNull();
    expect(vitalReport({ name: "LCP", value: 100 }, "/", 1440)).toBeNull();
    expect(vitalReport({ name: "LCP", value: 100 }, "/c/cafe", 1440)).toBeNull();
    expect(vitalReport({ name: "LCP", value: Number.NaN }, "/businesses", 1440)).toBeNull();
  });
});

import { describe, expect, it } from "vitest";

import { PAYMENT_PAGE_ROUTES, isPaymentPage } from "./paymentPages";

describe("isPaymentPage", () => {
  it("is the billing page of any business", () => {
    expect(isPaymentPage("/b/biz_1/settings/billing")).toBe(true);
    expect(isPaymentPage("/b/business_7f3/settings/billing/")).toBe(true);
  });

  it("is no other page, nor a page below the billing page", () => {
    for (const path of [
      "/login",
      "/b/biz_1/settings",
      "/b/biz_1/settings/deposits",
      "/b/biz_1/settings/billing/history",
      "/b/biz_1/overview",
      "/c/cafe-batumi",
      "/billing",
    ]) {
      expect(isPaymentPage(path), path).toBe(false);
    }
  });

  it("matches every route it lists, with any business in it", () => {
    for (const route of PAYMENT_PAGE_ROUTES) {
      expect(isPaymentPage(route.replace("[businessId]", "biz_42")), route).toBe(true);
    }
  });
});

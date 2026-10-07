import { describe, expect, it } from "vitest";

import {
  customerFiltersQuery,
  customerListQuery,
  hasCustomerFilters,
  NO_CUSTOMER_FILTERS,
  parseCustomerFilters,
  searchParam,
  tagParam,
} from "./customerFilters";

describe("the customer list's filters", () => {
  it("reads the URL and falls back to everyone", () => {
    expect(parseCustomerFilters({ q: "nino", tag: " regular ", show: "vip" })).toEqual({
      search: "nino",
      tag: "regular",
      show: "vip",
    });
    expect(parseCustomerFilters({ show: "everyone", tag: "   ", q: ["a", "b"] })).toEqual(NO_CUSTOMER_FILTERS);
    expect(parseCustomerFilters({ q: "x".repeat(150) }).search).toHaveLength(100);
  });

  it("sends a trimmed search and tag, or none", () => {
    expect(searchParam("  599 11 ")).toBe("599 11");
    expect(searchParam("   ")).toBeUndefined();
    expect(searchParam("x".repeat(150))).toHaveLength(100);
    expect(tagParam(null)).toBeUndefined();
    expect(tagParam(` ${"t".repeat(40)} `)).toHaveLength(32);
  });

  it("writes the URL in a fixed order and leaves out what is unset", () => {
    expect(customerFiltersQuery(NO_CUSTOMER_FILTERS)).toBe("");
    expect(customerFiltersQuery({ search: " ნინო ", tag: "VIP guest", show: "blocked" })).toBe(
      "q=%E1%83%9C%E1%83%98%E1%83%9C%E1%83%9D&tag=VIP+guest&show=blocked",
    );
    expect(hasCustomerFilters(NO_CUSTOMER_FILTERS)).toBe(false);
    expect(hasCustomerFilters({ ...NO_CUSTOMER_FILTERS, search: "  " })).toBe(false);
    expect(hasCustomerFilters({ ...NO_CUSTOMER_FILTERS, show: "vip" })).toBe(true);
  });

  it("asks the API with its own names", () => {
    expect(customerListQuery(NO_CUSTOMER_FILTERS)).toEqual({});
    expect(customerListQuery({ search: "Nino", tag: "regular", show: "vip" })).toEqual({
      search: "Nino",
      tag: "regular",
      filter: "vip",
    });
  });
});

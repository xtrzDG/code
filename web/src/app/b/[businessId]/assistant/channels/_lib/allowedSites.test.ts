import { describe, expect, it } from "vitest";

import { hasSite, isSameSiteList, siteLabel, siteOrigin } from "./allowedSites";

describe("siteOrigin", () => {
  it("reads an address as the API stores it: https by default, no path", () => {
    expect(siteOrigin("cafe-batumi.ge/menu?table=4")).toBe("https://cafe-batumi.ge");
    expect(siteOrigin("  https://Shop.Example.com/ ")).toBe("https://shop.example.com");
    expect(siteOrigin("http://shop.ge:8080/a")).toBe("http://shop.ge:8080");
    expect(siteOrigin("https://shop.ge:443")).toBe("https://shop.ge");
    expect(siteOrigin("http://localhost:3000")).toBe("http://localhost:3000");
  });

  it("refuses what is no website", () => {
    expect(siteOrigin("")).toBeNull();
    expect(siteOrigin("my shop")).toBeNull();
    expect(siteOrigin("intranet")).toBeNull();
    expect(siteOrigin("ftp://files.example.com")).toBeNull();
    expect(siteOrigin("javascript:alert(1)")).toBeNull();
    expect(siteOrigin("https://")).toBeNull();
  });
});

describe("hasSite", () => {
  it("counts www and the bare host, and both schemes, as one site", () => {
    const sites = ["https://cafe-batumi.ge"];

    expect(hasSite(sites, "https://www.cafe-batumi.ge")).toBe(true);
    expect(hasSite(sites, "http://cafe-batumi.ge")).toBe(true);
    expect(hasSite(sites, "https://cafe-batumi.ge:8443")).toBe(false);
    expect(hasSite(sites, "https://other.ge")).toBe(false);
  });
});

describe("siteLabel and isSameSiteList", () => {
  it("shows a site without its scheme and compares lists in order", () => {
    expect(siteLabel("https://cafe-batumi.ge")).toBe("cafe-batumi.ge");
    expect(siteLabel("http://shop.ge:8080")).toBe("shop.ge:8080");
    expect(isSameSiteList(["https://a.ge", "https://b.ge"], ["https://a.ge", "https://b.ge"])).toBe(true);
    expect(isSameSiteList(["https://a.ge", "https://b.ge"], ["https://b.ge", "https://a.ge"])).toBe(false);
    expect(isSameSiteList([], ["https://a.ge"])).toBe(false);
  });
});

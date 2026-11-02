import { describe, expect, it } from "vitest";

import { isAuditedExportPath, isCrossSiteRequest, isSameOriginRequest } from "./sameOrigin";

const SITE = { SITE_URL: "https://cabinet.example" };
const NO_SITE_URL = {};

function headers(values: Record<string, string>): Headers {
  return new Headers({ host: "cabinet.example", "x-forwarded-proto": "https", ...values });
}

describe("writes", () => {
  it("pass from the site's own pages", () => {
    expect(isCrossSiteRequest("POST", headers({ "sec-fetch-site": "same-origin" }), null, SITE)).toBe(false);
    expect(isCrossSiteRequest("PATCH", headers({ "sec-fetch-site": "same-origin", origin: "https://cabinet.example" }), null, SITE)).toBe(false);
    // A browser without Fetch Metadata: the Origin decides.
    expect(isCrossSiteRequest("DELETE", headers({ origin: "https://cabinet.example" }), null, SITE)).toBe(false);
    // Without SITE_URL: the address the request came in on (the e2e suite, previews).
    expect(isCrossSiteRequest("PUT", new Headers({ host: "localhost:3010", origin: "http://localhost:3010" }), null, NO_SITE_URL)).toBe(false);
    expect(
      isCrossSiteRequest(
        "POST",
        new Headers({ host: "internal:3000", "x-forwarded-host": "cabinet.example", "x-forwarded-proto": "https", origin: "https://cabinet.example" }),
        null,
        NO_SITE_URL,
      ),
    ).toBe(false);
  });

  it("are refused from another site, a sibling subdomain or a page the browser cannot name", () => {
    expect(isCrossSiteRequest("POST", headers({ "sec-fetch-site": "cross-site", origin: "https://evil.example" }), null, SITE)).toBe(true);
    expect(isCrossSiteRequest("POST", headers({ "sec-fetch-site": "same-site", origin: "https://blog.cabinet.example" }), null, SITE)).toBe(true);
    expect(isCrossSiteRequest("POST", headers({ "sec-fetch-site": "none" }), null, SITE)).toBe(true);
    expect(isCrossSiteRequest("POST", headers({ origin: "https://evil.example" }), null, SITE)).toBe(true);
    expect(isCrossSiteRequest("POST", headers({ origin: "null" }), null, SITE)).toBe(true);
    // A plain-HTTP page of the same host is another origin.
    expect(isCrossSiteRequest("POST", headers({ origin: "http://cabinet.example" }), null, SITE)).toBe(true);
    // Fetch Metadata wins over an Origin that names the site (a cross-site redirect chain).
    expect(isCrossSiteRequest("POST", headers({ "sec-fetch-site": "cross-site", origin: "https://cabinet.example" }), null, SITE)).toBe(true);
  });

  it("are refused when they carry neither Origin nor Sec-Fetch-Site", () => {
    expect(isCrossSiteRequest("POST", headers({}), null, SITE)).toBe(true);
    expect(isCrossSiteRequest("DELETE", new Headers({ host: "localhost:3010" }), null, NO_SITE_URL)).toBe(true);
    expect(isSameOriginRequest(headers({}), SITE)).toBe(false);
  });
});

describe("reads", () => {
  it("pass, also from another site, except an audited export", () => {
    expect(isCrossSiteRequest("GET", headers({ "sec-fetch-site": "cross-site" }), "/v1/businesses/b1/bookings", SITE)).toBe(false);
    expect(isCrossSiteRequest("GET", headers({ origin: "https://evil.example" }), null, SITE)).toBe(false);
    expect(isCrossSiteRequest("HEAD", headers({}), "/v1/me", SITE)).toBe(false);
  });

  it("refuse an audited export another site navigates or fetches to", () => {
    const exports = [
      "/v1/businesses/b1/exports/bookings",
      "/v1/business-exports/b1/export_1/download",
      "/v1/businesses/b1/contacts/contact_1/export",
      "/v1/businesses/b1/customer-segments/segment_1/export",
    ];
    for (const path of exports) {
      expect(isAuditedExportPath(path), path).toBe(true);
      expect(isCrossSiteRequest("GET", headers({ "sec-fetch-site": "cross-site", "sec-fetch-mode": "navigate" }), path, SITE), path).toBe(true);
      expect(isCrossSiteRequest("GET", headers({ "sec-fetch-site": "same-site" }), path, SITE), path).toBe(true);
      expect(isCrossSiteRequest("GET", headers({ origin: "https://evil.example" }), path, SITE), path).toBe(true);
      // The cabinet's own fetch and download link, a typed address, a client without Fetch Metadata.
      expect(isCrossSiteRequest("GET", headers({ "sec-fetch-site": "same-origin" }), path, SITE), path).toBe(false);
      expect(isCrossSiteRequest("GET", headers({ "sec-fetch-site": "none" }), path, SITE), path).toBe(false);
      expect(isCrossSiteRequest("GET", headers({}), path, SITE), path).toBe(false);
    }
    expect(isAuditedExportPath("/v1/businesses/b1/business-exports")).toBe(false);
    expect(isAuditedExportPath("/v1/businesses/b1/exports/bookings/x")).toBe(false);
  });
});

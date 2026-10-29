import { describe, expect, it } from "vitest";

import { siteOrigin } from "./siteOrigin";

function headersOf(values: Record<string, string>): Headers {
  return new Headers(values);
}

describe("site origin", () => {
  it("prefers SITE_URL and keeps only its origin", () => {
    expect(siteOrigin(headersOf({ host: "evil.example" }), { SITE_URL: "https://app.example.com/ru?x=1" })).toBe(
      "https://app.example.com",
    );
  });

  it("ignores a SITE_URL that is not an http(s) address", () => {
    expect(siteOrigin(headersOf({ host: "localhost:4033" }), { SITE_URL: "javascript:alert(1)" })).toBe("http://localhost:4033");
  });

  it("falls back to the forwarded host and protocol", () => {
    expect(
      siteOrigin(headersOf({ host: "internal:3000", "x-forwarded-host": "app.example.com", "x-forwarded-proto": "https" }), {}),
    ).toBe("https://app.example.com");
  });

  it("refuses a host that is not a plain host name", () => {
    expect(siteOrigin(headersOf({ host: "evil.example/<script>" }), {})).toBe("http://localhost:3000");
    expect(siteOrigin(headersOf({}), {})).toBe("http://localhost:3000");
  });
});

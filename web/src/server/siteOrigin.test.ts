import { describe, expect, it, vi } from "vitest";

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

  describe("in a production build without SITE_URL", () => {
    const production = { NODE_ENV: "production" };

    it("never names the host a visitor sent", () => {
      const error = vi.spyOn(console, "error").mockImplementation(() => undefined);

      expect(siteOrigin(headersOf({ host: "evil.example" }), production)).toBe("http://localhost:3000");
      expect(
        siteOrigin(headersOf({ host: "internal:3000", "x-forwarded-host": "evil.example", "x-forwarded-proto": "https" }), production),
      ).toBe("http://localhost:3000");
      expect(error.mock.calls.flat().join(" ")).toContain("SITE_URL is not set");
      error.mockRestore();
    });

    it("keeps this machine's own address (next start, the e2e suite)", () => {
      expect(siteOrigin(headersOf({ host: "localhost:3010" }), production)).toBe("http://localhost:3010");
      expect(siteOrigin(headersOf({ host: "127.0.0.1:3010" }), production)).toBe("http://127.0.0.1:3010");
    });

    it("still prefers SITE_URL", () => {
      expect(siteOrigin(headersOf({ host: "evil.example" }), { ...production, SITE_URL: "https://app.example.com" })).toBe(
        "https://app.example.com",
      );
    });
  });
});

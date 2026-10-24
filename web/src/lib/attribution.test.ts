import { describe, expect, it } from "vitest";

import {
  attributionOfVisit,
  decodeAttribution,
  encodeAttribution,
  isAttributionPage,
  sanitizeAttribution,
} from "./attribution";

const NOW_MS = 1_791_100_000_123;

describe("first-touch attribution", () => {
  it("is kept on the landing page and the hosted chat pages only", () => {
    expect(isAttributionPage("/")).toBe(true);
    expect(isAttributionPage("/c/cafe-batumi")).toBe(true);
    // "/?ref=…" redirects to the site in the reader's language with the same query.
    expect(isAttributionPage("/ru")).toBe(true);
    expect(isAttributionPage("/ka/restaurants")).toBe(true);
    expect(isAttributionPage("/rules")).toBe(false);
    expect(isAttributionPage("/login")).toBe(false);
    expect(isAttributionPage("/b/biz_1/overview")).toBe(false);
  });

  it("reads the link's campaign, ref and src, the referring host and the page", () => {
    const url = new URL(
      "https://workshop.example/?utm_source=Instagram&utm_medium=story&utm_campaign=Autumn%20launch&ref=partner-7&src=qr&fbclid=abc",
    );

    expect(attributionOfVisit(url, "https://l.instagram.com/some/path?x=1", NOW_MS)).toEqual({
      utm_source: "Instagram",
      utm_medium: "story",
      utm_campaign: "Autumn launch",
      referral_code: "partner-7",
      source_tag: "qr",
      referrer_host: "l.instagram.com",
      landing_path: "/",
      first_seen_at: NOW_MS * 1000,
    });
  });

  it("ignores this site as a referrer and anything the API would refuse", () => {
    const url = new URL("https://workshop.example/c/cafe?utm_source=%3Cscript%3E&ref=bad%20code&utm_term=" + "x".repeat(121));

    expect(attributionOfVisit(url, "https://workshop.example/", NOW_MS)).toEqual({
      landing_path: "/c/cafe",
      first_seen_at: NOW_MS * 1000,
    });
    expect(attributionOfVisit(url, "android-app://com.google", NOW_MS).referrer_host).toBeUndefined();
  });

  it("survives the cookie in Georgian and Russian campaign names", () => {
    const attribution = { utm_campaign: "შემოდგომა — осень", landing_path: "/", first_seen_at: 1 };

    const encoded = encodeAttribution(attribution);

    expect(encoded).toMatch(/^[A-Za-z0-9_-]+$/);
    expect(decodeAttribution(encoded)).toEqual(attribution);
  });

  it("refuses a cookie that is not its own", () => {
    expect(decodeAttribution(undefined)).toBeNull();
    expect(decodeAttribution("not base64!")).toBeNull();
    expect(decodeAttribution(encodeAttribution({}))).toBeNull();
    expect(decodeAttribution(btoa("[1,2]"))).toBeNull();
    expect(sanitizeAttribution({ utm_source: 7, first_seen_at: -1, referrer_host: "Example.COM" })).toBeNull();
  });
});

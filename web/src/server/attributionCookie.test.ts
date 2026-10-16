import { NextRequest, NextResponse } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ATTRIBUTION_COOKIE, decodeAttribution, encodeAttribution } from "@/lib/attribution";

import { forgetAttribution, rememberFirstVisit, withSignupAttribution } from "./attributionCookie";

const NOW_MS = 1_791_100_000_000;

function visit(url: string, headers: Record<string, string> = {}): NextRequest {
  return new NextRequest(url, { headers });
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("attribution cookie", () => {
  it("is set on a first visit to the landing page, httpOnly for 90 days", () => {
    vi.stubEnv("COOKIE_SECURE", "true");
    const response = NextResponse.next();

    rememberFirstVisit(visit("https://workshop.example/?utm_source=google", { referer: "https://www.google.com/" }), response, NOW_MS);

    const cookie = response.cookies.get(ATTRIBUTION_COOKIE);
    expect(cookie).toMatchObject({ httpOnly: true, secure: true, sameSite: "lax", path: "/", maxAge: 90 * 24 * 60 * 60 });
    expect(decodeAttribution(cookie?.value)).toEqual({
      utm_source: "google",
      referrer_host: "www.google.com",
      landing_path: "/",
      first_seen_at: NOW_MS * 1000,
    });
  });

  it("keeps the first touch, and is not set for signed-in people, other pages or redirects", () => {
    const cases: [NextRequest, NextResponse][] = [
      [visit("https://workshop.example/?utm_source=b", { cookie: `${ATTRIBUTION_COOKIE}=first` }), NextResponse.next()],
      [visit("https://workshop.example/", { cookie: "aw_session=tok" }), NextResponse.next()],
      [visit("https://workshop.example/login?utm_source=x"), NextResponse.next()],
      [visit("https://workshop.example/c/cafe"), NextResponse.redirect("https://workshop.example/c/new-cafe", 308)],
    ];
    for (const [request, response] of cases) {
      rememberFirstVisit(request, response, NOW_MS);
      expect(response.cookies.get(ATTRIBUTION_COOKIE)).toBeUndefined();
    }
  });

  it("goes with the sign-in as signup_attribution; the browser's own value never does", () => {
    const cookie = encodeAttribution({ utm_source: "instagram", landing_path: "/" });

    const sent = JSON.parse(
      withSignupAttribution(JSON.stringify({ challenge_id: "c", code: "123456", signup_attribution: { utm_source: "forged" } }), cookie),
    ) as Record<string, unknown>;
    const without = JSON.parse(
      withSignupAttribution(JSON.stringify({ challenge_id: "c", code: "1", signup_attribution: { x: 1 } }), "garbage!"),
    ) as Record<string, unknown>;

    expect(sent).toEqual({ challenge_id: "c", code: "123456", signup_attribution: { utm_source: "instagram", landing_path: "/" } });
    expect(without).toEqual({ challenge_id: "c", code: "1" });
    expect(withSignupAttribution("not json", cookie)).toBe("not json");
    expect(withSignupAttribution("[1]", cookie)).toBe("[1]");
  });

  it("is dropped after the sign-in", () => {
    const response = NextResponse.json({});

    forgetAttribution(response);

    expect(response.cookies.get(ATTRIBUTION_COOKIE)).toMatchObject({ value: "", maxAge: 0 });
  });
});

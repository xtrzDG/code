import { NextResponse } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CONSENT_COOKIE, CONSENT_MAX_AGE_SECONDS, hasAttributionConsent, parseConsent, readConsent, setConsentCookie } from "./consentCookie";

function cookies(values: Record<string, string>) {
  return { get: (name: string) => (name in values ? { value: values[name] ?? "" } : undefined) };
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("the consent cookie", () => {
  it("reads only an answer to the current question", () => {
    expect(parseConsent("1.granted")).toBe("granted");
    expect(parseConsent("1.denied")).toBe("denied");
    // No answer yet, an answer to an older question, anything else: ask.
    expect(parseConsent(undefined)).toBeNull();
    expect(parseConsent("0.granted")).toBeNull();
    expect(parseConsent("granted")).toBeNull();
    expect(readConsent(cookies({ [CONSENT_COOKIE]: "1.denied" }))).toBe("denied");
  });

  it("lets the attribution cookie in only after an acceptance", () => {
    expect(hasAttributionConsent(cookies({ [CONSENT_COOKIE]: "1.granted" }))).toBe(true);
    expect(hasAttributionConsent(cookies({ [CONSENT_COOKIE]: "1.denied" }))).toBe(false);
    expect(hasAttributionConsent(cookies({}))).toBe(false);
  });

  it("is a technical cookie kept for six months, httpOnly and Secure over HTTPS", () => {
    vi.stubEnv("COOKIE_SECURE", "true");
    const response = NextResponse.json({});

    setConsentCookie(response, "denied", new Headers({ host: "cabinet.example" }));

    expect(CONSENT_MAX_AGE_SECONDS).toBe(183 * 24 * 60 * 60);
    expect(response.cookies.get(CONSENT_COOKIE)).toMatchObject({
      value: "1.denied",
      httpOnly: true,
      secure: true,
      sameSite: "lax",
      path: "/",
      maxAge: CONSENT_MAX_AGE_SECONDS,
    });
  });
});

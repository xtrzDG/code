// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/** A fresh module per test: where the visit began is kept for the page load. */
async function loadSaveConsent() {
  vi.resetModules();
  return import("./saveConsent");
}

function stubConsentRoute() {
  const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => new Response(null, { status: 204 }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function sentBody(fetchMock: ReturnType<typeof stubConsentRoute>): Record<string, unknown> {
  return JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body)) as Record<string, unknown>;
}

function cameFrom(referrer: string): void {
  Object.defineProperty(document, "referrer", { configurable: true, get: () => referrer });
}

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  cameFrom("");
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("saving the cookie choice", () => {
  it("sends with an acceptance the page the visit began on and the site before it", async () => {
    const { hasAnsweredHere, rememberArrival, saveConsent } = await loadSaveConsent();
    const fetchMock = stubConsentRoute();
    window.history.replaceState(null, "", "/en?ref=invite-code-01&src=invite");
    cameFrom("https://partner.example/post");
    rememberArrival();

    // The visitor opens another page of the site before accepting.
    window.history.pushState(null, "", "/en/for/hotel");
    rememberArrival();
    expect(hasAnsweredHere()).toBe(false);
    expect(await saveConsent("granted")).toBe(true);
    expect(hasAnsweredHere()).toBe(true);

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/consent");
    expect(sentBody(fetchMock)).toEqual({
      choice: "granted",
      page: "/en?ref=invite-code-01&src=invite",
      referrer: "https://partner.example/post",
    });
  });

  it("never names one of the site's own pages as where the visitor came from", async () => {
    const { rememberArrival, saveConsent } = await loadSaveConsent();
    const fetchMock = stubConsentRoute();
    window.history.replaceState(null, "", "/it/terms");
    cameFrom(`${window.location.origin}/it`);
    rememberArrival();

    await saveConsent("granted");

    expect(sentBody(fetchMock)).toEqual({ choice: "granted", page: "/it/terms" });
  });

  it("uses the current page when the banner never noted one, and sends nothing but the answer with a rejection", async () => {
    const { saveConsent } = await loadSaveConsent();
    const fetchMock = stubConsentRoute();
    window.history.replaceState(null, "", "/en/cookies?utm_source=mail");

    await saveConsent("granted");
    await saveConsent("denied");

    expect(sentBody(fetchMock)).toEqual({ choice: "granted", page: "/en/cookies?utm_source=mail" });
    expect(JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body))).toEqual({ choice: "denied" });
  });

  it("reports a choice it could not store", async () => {
    const { hasAnsweredHere, saveConsent } = await loadSaveConsent();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("offline");
      }),
    );

    expect(await saveConsent("denied")).toBe(false);
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 500 })));
    expect(await saveConsent("denied")).toBe(false);
    // The banner asks again on the next page.
    expect(hasAnsweredHere()).toBe(false);
  });
});

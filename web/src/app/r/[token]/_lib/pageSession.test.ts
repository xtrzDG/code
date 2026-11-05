// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { failure, ok } from "@/test/fakeApi";

import { hideLinkToken, lastPageLanguage, openPageSession, readPageSession, storePageSession } from "./pageSession";
import { PAGE_SESSION_PATH } from "./pageSessionPath";
import { privacyNoticeOfView } from "./privacyNotice";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const LINK = "l".repeat(76);
const CREDENTIAL = "s".repeat(76);
const NOW = 1_790_000_000_000_000;

describe("the booking page's credential", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    vi.mocked(api.POST).mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("is traded for the link's token", async () => {
    vi.mocked(api.POST).mockReturnValue(ok({ token: CREDENTIAL, expires_at: NOW + 1_800_000_000 }) as never);

    const session = await openPageSession(LINK, "it");

    expect(api.POST).toHaveBeenCalledWith("/v1/public/bookings/{token}/session", { params: { path: { token: LINK } } });
    expect(session).toEqual({ token: CREDENTIAL, expiresAt: NOW + 1_800_000_000, language: "it" });
  });

  it("fails as the API refused it", async () => {
    vi.mocked(api.POST).mockReturnValue(failure(429, { message: "Too many requests", reasons: [] }) as never);

    await expect(openPageSession(LINK, "en")).rejects.toBeTruthy();
  });

  it("is kept for the tab until it ends", () => {
    expect(storePageSession({ token: CREDENTIAL, expiresAt: NOW + 10, language: "it" })).toBe(true);

    expect(readPageSession(NOW)).toEqual({ token: CREDENTIAL, expiresAt: NOW + 10, language: "it" });
    expect(readPageSession(NOW + 10)).toBeNull();
    // The language stays known for the page that says it closed.
    expect(lastPageLanguage()).toBe("it");
  });

  it("reads nothing from a tab that kept nothing or something else", () => {
    expect(readPageSession(NOW)).toBeNull();
    window.sessionStorage.setItem("aw_booking_page", "{not json");
    expect(readPageSession(NOW)).toBeNull();
    window.sessionStorage.setItem("aw_booking_page", JSON.stringify({ token: 1 }));
    expect(readPageSession(NOW)).toBeNull();
    expect(lastPageLanguage()).toBeNull();
  });

  it("says when the browser keeps nothing", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });

    expect(storePageSession({ token: CREDENTIAL, expiresAt: NOW, language: "en" })).toBe(false);
  });

  it("takes the token out of the address bar", () => {
    const replace = vi.spyOn(window.history, "replaceState");

    hideLinkToken();

    expect(replace).toHaveBeenCalledWith(null, "", PAGE_SESSION_PATH);
    expect(PAGE_SESSION_PATH).toBe("/r/booking");
  });
});

describe("privacyNoticeOfView", () => {
  const base = { chat_links: [{ kind: "hosted_chat", url: "https://app.example/c/salobie" }] } as never;

  it("is the notice the API names first", () => {
    expect(privacyNoticeOfView({ ...(base as object), privacy_url: "https://salobie.example/privacy" } as never)).toBe(
      "https://salobie.example/privacy",
    );
  });

  it("is the chat page's notice without one", () => {
    expect(privacyNoticeOfView(base)).toBe("https://app.example/c/salobie/privacy");
    expect(privacyNoticeOfView({ chat_links: [] } as never)).toBeNull();
  });
});

import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ConsentBanner as ConsentBannerComponent, ConsentBannerTexts } from "./ConsentBanner";
import type { CookieSettingsButton as CookieSettingsButtonComponent } from "./CookieSettingsButton";

/** A fresh banner module per test: an answer given in one test is kept for that page load. */
let ConsentBanner: typeof ConsentBannerComponent;
let CookieSettingsButton: typeof CookieSettingsButtonComponent;

beforeEach(async () => {
  vi.resetModules();
  ({ ConsentBanner } = await import("./ConsentBanner"));
  ({ CookieSettingsButton } = await import("./CookieSettingsButton"));
});

const TEXTS: ConsentBannerTexts = {
  title: "Cookies on this site",
  text: "We use the cookies the site needs.",
  statementLink: "Read the cookie statement",
  statementHref: "/en/cookies",
  accept: "Accept",
  reject: "Reject",
  close: "Close and continue without accepting",
  failed: "Your choice could not be saved.",
};

function stubConsentRoute(ok = true) {
  const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => new Response(null, { status: ok ? 204 : 500 }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function sentChoice(fetchMock: ReturnType<typeof stubConsentRoute>, call = 0): Record<string, unknown> {
  const [url, init] = fetchMock.mock.calls[call] ?? [];
  expect(url).toBe("/api/consent");
  return JSON.parse(String(init?.body)) as Record<string, unknown>;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the cookie banner", () => {
  it("offers Accept and Reject side by side in the same style, with the statement linked", () => {
    render(<ConsentBanner texts={TEXTS} initiallyOpen />);

    const region = screen.getByRole("region", { name: TEXTS.title });
    const accept = screen.getByRole("button", { name: TEXTS.accept });
    const reject = screen.getByRole("button", { name: TEXTS.reject });
    expect(region.tagName).toBe("SECTION");
    expect(accept.className).toBe(reject.className);
    expect(screen.getByRole("link", { name: TEXTS.statementLink }).getAttribute("href")).toBe("/en/cookies");
  });

  it("stores an acceptance with the page it was given on", async () => {
    const fetchMock = stubConsentRoute();
    render(<ConsentBanner texts={TEXTS} initiallyOpen />);

    await userEvent.click(screen.getByRole("button", { name: TEXTS.accept }));

    await waitFor(() => expect(screen.queryByRole("region", { name: TEXTS.title })).toBeNull());
    expect(sentChoice(fetchMock)).toMatchObject({ choice: "granted", page: "/" });
  });

  it("stays closed on a page brought back from the router's cache after the answer (the Back button)", async () => {
    stubConsentRoute();
    const { unmount } = render(<ConsentBanner texts={TEXTS} initiallyOpen />);
    await userEvent.click(screen.getByRole("button", { name: TEXTS.reject }));
    await waitFor(() => expect(screen.queryByRole("region", { name: TEXTS.title })).toBeNull());
    unmount();

    // The cached page was rendered while the question was open.
    render(<ConsentBanner texts={TEXTS} initiallyOpen />);

    expect(screen.queryByRole("region", { name: TEXTS.title })).toBeNull();
  });

  it("treats Reject, the close button and Escape alike: a rejection", async () => {
    for (const close of [
      () => userEvent.click(screen.getByRole("button", { name: TEXTS.reject })),
      () => userEvent.click(screen.getByRole("button", { name: TEXTS.close })),
      async () => {
        screen.getByRole("button", { name: TEXTS.accept }).focus();
        await userEvent.keyboard("{Escape}");
      },
    ]) {
      const fetchMock = stubConsentRoute();
      // Each way of closing on a page load of its own.
      vi.resetModules();
      const { ConsentBanner: Banner } = await import("./ConsentBanner");
      const { unmount } = render(<Banner texts={TEXTS} initiallyOpen />);

      await close();

      await waitFor(() => expect(screen.queryByRole("region", { name: TEXTS.title })).toBeNull());
      expect(sentChoice(fetchMock)).toEqual({ choice: "denied" });
      unmount();
    }
  });

  it("stays open and says so when the choice could not be saved", async () => {
    stubConsentRoute(false);
    render(<ConsentBanner texts={TEXTS} initiallyOpen />);

    await userEvent.click(screen.getByRole("button", { name: TEXTS.reject }));

    expect((await screen.findByRole("alert")).textContent).toBe(TEXTS.failed);
    expect(screen.getByRole("region", { name: TEXTS.title })).toBeTruthy();
  });

  it("is hidden after an answer and comes back from Cookie settings, focus returning there", async () => {
    stubConsentRoute();
    render(
      <>
        <ConsentBanner texts={TEXTS} initiallyOpen={false} />
        <CookieSettingsButton label="Cookie settings" />
      </>,
    );
    expect(screen.queryByRole("region", { name: TEXTS.title })).toBeNull();

    const settings = screen.getByRole("button", { name: "Cookie settings" });
    await userEvent.click(settings);
    expect(screen.getByRole("region", { name: TEXTS.title })).toBeTruthy();
    await act(async () => {
      await userEvent.click(screen.getByRole("button", { name: TEXTS.accept }));
    });

    await waitFor(() => expect(screen.queryByRole("region", { name: TEXTS.title })).toBeNull());
    expect(document.activeElement).toBe(settings);
  });
});

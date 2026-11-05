import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import type { Schema } from "@/api/types";
import { bookingPageTexts } from "@/lib/bookingPage/texts";
import { answerGet, failure, ok } from "@/test/fakeApi";
import { renderInLocale } from "@/test/render";

import { readPageSession, storePageSession } from "../_lib/pageSession";
import { ManagedBooking } from "./ManagedBooking";
import { RestoredBooking } from "./RestoredBooking";

vi.mock("@/api/client", () => ({ BFF_BASE_PATH: "/api/backend", api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const LINK = "l".repeat(76);
const CREDENTIAL = "s".repeat(76);
const SESSION = "/v1/public/bookings/{token}/session";
const CANCEL = "/v1/public/bookings/{token}/cancel";
const ENDS = Date.now() * 1000 + 1_800_000_000;

const view = {
  token: LINK,
  business_name: "Mtsvane Ezo",
  booking_unit: "time_slot",
  status: "confirmed",
  date: "2026-10-08",
  end_date: "2026-10-08",
  time: "19:00",
  end_time: "21:00",
  timezone: "Asia/Tbilisi",
  language: "it",
  party_size: 2,
  can_cancel: true,
  can_reschedule: true,
  is_over: false,
  marketing_consent: false,
  privacy_url: "https://mtsvane.example/privacy",
} as Schema<"ManagedBookingView">;

const it_texts = bookingPageTexts("it");

function answerPost(answers: Record<string, () => Promise<unknown>>) {
  vi.mocked(api.POST).mockImplementation(((path: string) => {
    const answer = answers[path];
    if (!answer) throw new Error(`unexpected POST ${path}`);
    return answer();
  }) as never);
}

describe("ManagedBooking: the link's token leaves the address bar", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    vi.mocked(api.POST).mockReset();
    vi.mocked(api.GET).mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("trades the token, keeps the credential for the tab and uses it from then on", async () => {
    const replace = vi.spyOn(window.history, "replaceState");
    answerPost({
      [SESSION]: () => ok({ token: CREDENTIAL, expires_at: ENDS }),
      [CANCEL]: () => ok({ ...view, token: CREDENTIAL, status: "cancelled", can_cancel: false, can_reschedule: false }),
    });
    renderInLocale(<ManagedBooking initialView={view} texts={it_texts} language="it" />, { locale: "it" });

    await waitFor(() => expect(replace).toHaveBeenCalledWith(null, "", "/r/booking"));
    expect(api.POST).toHaveBeenCalledWith(SESSION, { params: { path: { token: LINK } } });
    expect(readPageSession()).toEqual({ token: CREDENTIAL, expiresAt: ENDS, language: "it" });

    await userEvent.click(screen.getByRole("button", { name: it_texts.cancel }));
    await userEvent.click(screen.getByRole("button", { name: it_texts.confirmCancel }));

    expect(api.POST).toHaveBeenLastCalledWith(CANCEL, { params: { path: { token: CREDENTIAL } } });
    const calendar = screen.queryByRole("link", { name: it_texts.addToCalendar });
    expect(calendar === null || !calendar.getAttribute("href")?.includes(LINK)).toBe(true);
  });

  it("says the page closed, not that the link expired, once its credential ended", async () => {
    const expired = () =>
      failure(404, { error: "not_found", message: "expired", reasons: [{ code: "link_expired", message: "expired" }] });
    answerPost({ [CANCEL]: expired });
    renderInLocale(
      <ManagedBooking initialView={{ ...view, token: CREDENTIAL }} texts={it_texts} language="it" sessionExpiresAt={ENDS} />,
      { locale: "it" },
    );

    await userEvent.click(screen.getByRole("button", { name: it_texts.cancel }));
    await userEvent.click(screen.getByRole("button", { name: it_texts.confirmCancel }));

    expect(await screen.findByText(it_texts.pageClosed)).toBeTruthy();
    expect(screen.queryByText(it_texts.linkExpired)).toBeNull();
    expect(screen.queryByRole("button", { name: it_texts.cancel })).toBeNull();
    expect(api.POST).not.toHaveBeenCalledWith(SESSION, expect.anything());
  });

  it("keeps telling a guest on their link that the link expired", async () => {
    const expired = () =>
      failure(404, { error: "not_found", message: "expired", reasons: [{ code: "link_expired", message: "expired" }] });
    answerPost({ [SESSION]: () => failure(429, { message: "Too many requests", reasons: [] }), [CANCEL]: expired });
    renderInLocale(<ManagedBooking initialView={view} texts={it_texts} language="it" />, { locale: "it" });
    await waitFor(() => expect(api.POST).toHaveBeenCalledTimes(1));

    await userEvent.click(screen.getByRole("button", { name: it_texts.cancel }));
    await userEvent.click(screen.getByRole("button", { name: it_texts.confirmCancel }));

    expect(await screen.findByText(it_texts.linkExpired)).toBeTruthy();
    expect(screen.queryByText(it_texts.pageClosed)).toBeNull();
  });

  it("keeps the link when the trade is refused", async () => {
    const replace = vi.spyOn(window.history, "replaceState");
    answerPost({ [SESSION]: () => failure(429, { message: "Too many requests", reasons: [] }) });

    renderInLocale(<ManagedBooking initialView={view} texts={it_texts} language="it" />, { locale: "it" });

    await waitFor(() => expect(api.POST).toHaveBeenCalledTimes(1));
    expect(replace).not.toHaveBeenCalled();
    expect(readPageSession()).toBeNull();
    expect(screen.getByRole("link", { name: it_texts.addToCalendar }).getAttribute("href")).toContain(LINK);
  });
});

describe("RestoredBooking: a reload of /r/booking", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    vi.mocked(api.POST).mockReset();
    vi.mocked(api.GET).mockReset();
  });

  it("opens the booking with the tab's credential, without trading again", async () => {
    storePageSession({ token: CREDENTIAL, expiresAt: ENDS, language: "it" });
    answerGet((path, init) => {
      expect(path).toBe("/v1/public/bookings/{token}");
      expect(init.params?.path?.token).toBe(CREDENTIAL);
      return ok({ ...view, token: CREDENTIAL });
    });

    renderInLocale(<RestoredBooking />, { locale: "it" });

    expect(await screen.findByRole("heading", { name: it_texts.pageTitle })).toBeTruthy();
    expect(api.POST).not.toHaveBeenCalled();
    expect(screen.getByRole("main").getAttribute("lang")).toBe("it");
    expect(screen.getByTestId("customer-page-links").innerHTML).toContain("https://mtsvane.example/privacy");
  });

  it("opens the platform's privacy notice, named by its full address on this site, in place", async () => {
    storePageSession({ token: CREDENTIAL, expiresAt: ENDS, language: "it" });
    answerGet(() => ok({ ...view, token: CREDENTIAL, privacy_url: `${window.location.origin}/c/mtsvane-ezo/privacy` }));

    renderInLocale(<RestoredBooking />, { locale: "it" });

    const privacy = await screen.findByRole("link", { name: "Informativa privacy" });
    expect(privacy.getAttribute("href")).toBe("/c/mtsvane-ezo/privacy");
    expect(privacy.getAttribute("target")).toBeNull();
  });

  it("asks to open the link again once the credential ended", async () => {
    storePageSession({ token: CREDENTIAL, expiresAt: Date.now() * 1000 - 1, language: "it" });

    renderInLocale(<RestoredBooking />, { locale: "it" });

    expect(await screen.findByText(it_texts.pageClosed)).toBeTruthy();
    expect(screen.getByRole("heading", { name: it_texts.errorTitle })).toBeTruthy();
    expect(api.GET).not.toHaveBeenCalled();
  });

  it("asks to open the link again when the API no longer takes the credential", async () => {
    storePageSession({ token: CREDENTIAL, expiresAt: ENDS, language: "it" });
    answerGet(() => failure(404, { message: "expired", reasons: [{ code: "link_expired", message: "expired" }] }));

    renderInLocale(<RestoredBooking />, { locale: "it" });

    expect(await screen.findByText(it_texts.pageClosed)).toBeTruthy();
  });
});

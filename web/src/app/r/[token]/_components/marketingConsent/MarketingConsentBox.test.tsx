import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import type { Schema } from "@/api/types";
import { failure, ok } from "@/test/fakeApi";
import { renderInLocale } from "@/test/render";

import { MARKETING_CONSENT_TEXT_VERSION, marketingConsentTexts } from "./consentTexts";
import { MarketingConsentBox } from "./MarketingConsentBox";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const CONSENT = "/v1/public/bookings/{token}/marketing-consent";

const view = {
  token: "t".repeat(48),
  business_name: "Mtsvane Ezo",
  booking_unit: "time_slot",
  status: "confirmed",
  date: "2026-10-08",
  end_date: "2026-10-08",
  timezone: "Asia/Tbilisi",
  language: "it",
  party_size: 2,
  can_cancel: true,
  can_reschedule: true,
  is_over: false,
  marketing_consent: false,
} as Schema<"ManagedBookingView">;

function renderBox(current = view) {
  const onChanged = vi.fn();
  const onProblem = vi.fn();
  renderInLocale(<MarketingConsentBox view={current} language="it" onChanged={onChanged} onProblem={onProblem} />);
  return { onChanged, onProblem, box: screen.getByRole("checkbox", { name: /Mtsvane Ezo/ }) };
}

describe("MarketingConsentBox", () => {
  beforeEach(() => {
    vi.mocked(api.POST).mockReset();
  });

  it("is unticked until the guest ticks it, in the guest's language", () => {
    const { box } = renderBox();

    expect(box).not.toBeChecked();
    expect(box).toHaveAccessibleName(/novità, offerte e inviti a tornare/);
    expect(box).toHaveAccessibleDescription(marketingConsentTexts("it").note);
  });

  it("records a tick with the wording's version and shows what was stored", async () => {
    vi.mocked(api.POST).mockReturnValue(ok({ ...view, marketing_consent: true }) as never);
    const { box, onChanged } = renderBox();

    await userEvent.click(box);

    expect(api.POST).toHaveBeenCalledWith(CONSENT, {
      params: { path: { token: view.token } },
      body: { is_given: true, text_version: MARKETING_CONSENT_TEXT_VERSION },
    });
    expect(onChanged).toHaveBeenCalledWith(expect.objectContaining({ marketing_consent: true }));
  });

  it("takes the consent back when the guest unticks it", async () => {
    vi.mocked(api.POST).mockReturnValue(ok({ ...view, marketing_consent: false }) as never);
    const { box } = renderBox({ ...view, marketing_consent: true });
    expect(box).toBeChecked();

    await userEvent.click(box);

    expect(api.POST).toHaveBeenCalledWith(CONSENT, expect.objectContaining({ body: expect.objectContaining({ is_given: false }) }));
  });

  it("goes back and says so when the choice was not saved", async () => {
    vi.mocked(api.POST).mockReturnValue(failure(503, { code: "service_unavailable", message: "Down." }) as never);
    const { box, onChanged, onProblem } = renderBox();

    await userEvent.click(box);

    expect(await screen.findByRole("alert")).toHaveTextContent(marketingConsentTexts("it").failed);
    expect(box).not.toBeChecked();
    expect(onChanged).not.toHaveBeenCalled();
    expect(onProblem).not.toHaveBeenCalled();
  });

  it("leaves a link that stopped working to the page", async () => {
    vi.mocked(api.POST).mockReturnValue(
      failure(404, { code: "not_found", message: "Gone.", reasons: [{ code: "link_expired", message: "Expired." }] }) as never,
    );
    const { box, onProblem } = renderBox();

    await userEvent.click(box);

    expect(onProblem).toHaveBeenCalledWith("linkExpired");
  });
});

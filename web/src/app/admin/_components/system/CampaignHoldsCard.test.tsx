import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import { answerGet, failure, ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import type { CampaignHold } from "../../_lib/useCampaignHolds";
import { CampaignHoldsCard } from "./CampaignHoldsCard";

vi.mock("@/api/client", () => ({
  api: {
    GET: vi.fn(),
    POST: vi.fn(),
    PUT: vi.fn(),
    PATCH: vi.fn(),
    DELETE: vi.fn(),
  },
}));

const hold: CampaignHold = {
  business_id: "business_7",
  held_at: Date.UTC(2026, 10, 2, 9, 0) * 1000,
  sent: 41,
  opted_out: 3,
};

describe("CampaignHoldsCard: campaigns held over their opt-out rate", () => {
  beforeEach(() => {
    queryCache.clear();
    vi.mocked(api.POST).mockReset();
  });

  it.each(["en", "it"] as const)(
    "lists a held campaign with its figures in %s",
    async (locale) => {
      const { t } = textsIn(locale);
      answerGet(() => ok({ items: [hold] }));
      renderInLocale(<CampaignHoldsCard canRelease={false} />, { locale });

      const table = await screen.findByRole("table", {
        name: t("platformBrakes.campaignHolds.title"),
      });
      expect(
        within(table).getByRole("link", { name: "business_7" }),
      ).toBeTruthy();
      expect(
        within(table).getByText(
          t("platformBrakes.campaignHolds.optedOutOf", {
            optedOut: "3",
            sent: "41",
          }),
        ),
      ).toBeTruthy();
      // Only a SUPER admin gets the button.
      expect(
        within(table).queryByRole("button", {
          name: t("platformBrakes.campaignHolds.release"),
        }),
      ).toBeNull();
    },
  );

  it("lets a SUPER admin release a campaign with a reason", async () => {
    const { t } = textsIn("en");
    answerGet(() => ok({ items: [hold] }));
    vi.mocked(api.POST).mockImplementation((() => ok(hold)) as never);
    renderInLocale(<CampaignHoldsCard canRelease />);

    fireEvent.click(
      await screen.findByRole("button", {
        name: t("platformBrakes.campaignHolds.release"),
      }),
    );
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByRole("textbox"), {
      target: { value: "  Agreed a consent-only segment " },
    });
    fireEvent.click(
      within(dialog).getByRole("button", {
        name: t("platformBrakes.campaignHolds.release"),
      }),
    );

    await waitFor(() => expect(api.POST).toHaveBeenCalledTimes(1));
    expect(vi.mocked(api.POST).mock.calls[0]).toEqual([
      "/v1/admin/campaign-holds/{business_id}/release",
      {
        params: { path: { business_id: "business_7" } },
        body: { reason: "Agreed a consent-only segment" },
      },
    ]);
  });

  it("shows nothing while no campaign is held", async () => {
    answerGet(() => ok({ items: [] }));
    const { container } = renderInLocale(<CampaignHoldsCard canRelease />);

    await waitFor(() => expect(api.GET).toHaveBeenCalled());
    await waitFor(() => expect(container.textContent).toBe(""));
  });

  it("is hidden from an admin whose role may not see operations", async () => {
    answerGet(() =>
      failure(403, {
        detail: "Your platform admin role does not include this.",
      }),
    );
    const { container } = renderInLocale(
      <CampaignHoldsCard canRelease={false} />,
    );

    await waitFor(() => expect(api.GET).toHaveBeenCalled());
    await waitFor(() => expect(container.textContent).toBe(""));
  });
});

import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import type { BusinessView, CurrentUserView, SecurityNudgeView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { answerGet, ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { SecurityNudgeBanner } from "./SecurityNudgeBanner";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() } }));
vi.mock("next/navigation", () => ({ usePathname: () => "/b/business_1/bookings" }));

const NUDGE = "/v1/businesses/{business_id}/security-nudge";
const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;
const live = { id: "business_1", name: "Café Tbilisi", status: "live", viewer_role: "owner" } as unknown as BusinessView;

const shown: SecurityNudgeView = {
  is_shown: true,
  is_owner: true,
  has_second_factor: false,
  team_size: 1,
  reason: "protect_customers",
};

function renderBanner(business: BusinessView = live, locale: "en" | "ru" | "ka" | "he" | "de" = "en") {
  return renderInLocale(
    <BusinessProvider business={business} me={me}>
      <SecurityNudgeBanner />
    </BusinessProvider>,
    { locale },
  );
}

describe("SecurityNudgeBanner: the owner's reminder to turn on a second factor", () => {
  beforeEach(() => {
    queryCache.clear();
    vi.mocked(api.GET).mockReset();
    vi.mocked(api.PUT).mockReset();
  });

  it.each(["en", "ru", "ka", "he", "de"] as const)("asks the owner of a live business, in %s", async (locale) => {
    const { t } = textsIn(locale);
    answerGet((path) => {
      expect(path).toBe(NUDGE);
      return ok(shown);
    });
    renderBanner(live, locale);

    const banner = await screen.findByRole("region", { name: t("securityNudge.title") });
    expect(banner.textContent).toContain(t("securityNudge.description"));
    const action = screen.getByRole("link", { name: t("securityNudge.action") });
    // Back to the page the owner was on once the factor is set up.
    expect(action.getAttribute("href")).toBe(`/account/security?next=${encodeURIComponent("/b/business_1/bookings")}`);
  });

  it("says why it is back once the team has grown", async () => {
    const { t } = textsIn("en");
    answerGet(() => ok({ ...shown, team_size: 3, reason: "team_grew" }));
    renderBanner();

    expect(await screen.findByText(t("securityNudge.teamGrew"))).toBeTruthy();
    expect(screen.queryByText(t("securityNudge.description"))).toBeNull();
  });

  it("is put away with Not now and stays away", async () => {
    const { t } = textsIn("en");
    let view = shown;
    answerGet(() => ok(view));
    vi.mocked(api.PUT).mockImplementation((() => {
      view = { ...shown, is_shown: false, dismissed_at: 1 };
      return ok(view);
    }) as never);
    renderBanner();

    await userEvent.click(await screen.findByRole("button", { name: t("securityNudge.dismissLabel") }));

    expect(vi.mocked(api.PUT)).toHaveBeenCalledWith("/v1/businesses/{business_id}/security-nudge/dismissal", {
      params: { path: { business_id: "business_1" } },
    });
    await waitFor(() => expect(screen.queryByRole("region", { name: t("securityNudge.title") })).toBeNull());
  });

  it("shows nothing when the API says not to (a second factor is on)", async () => {
    answerGet(() => ok({ ...shown, is_shown: false, has_second_factor: true, reason: null }));
    renderBanner();

    await waitFor(() => expect(vi.mocked(api.GET)).toHaveBeenCalled());
    expect(screen.queryByTestId("security-nudge")).toBeNull();
  });

  it("never asks staff, nor asks the API for them", () => {
    renderBanner({ ...live, viewer_role: "staff" });

    expect(vi.mocked(api.GET)).not.toHaveBeenCalled();
    expect(screen.queryByTestId("security-nudge")).toBeNull();
  });
});

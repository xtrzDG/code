import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import type { BusinessView, CurrentUserView, Schema } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { answerGet, ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { AssistantControlsCard } from "./AssistantControlsCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), PUT: vi.fn() } }));
vi.mock("next/navigation", () => ({ usePathname: () => "/b/business_1/settings", useRouter: () => ({ refresh: vi.fn() }) }));

const SETTINGS = "/v1/businesses/{business_id}/assistant-settings";
const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;
const business = { id: "business_1", name: "Trattoria Sole", status: "live", viewer_role: "owner" } as unknown as BusinessView;
const stored: Schema<"AssistantSettingsView"> = {
  remembers_customers: false,
  shares_team_notes: false,
  is_paused: false,
  disabled_tools: ["send_link"],
  updated_at: null,
};

function renderCard(role: "owner" | "staff" = "owner", locale: "en" | "it" = "en") {
  return renderInLocale(
    <BusinessProvider business={{ ...business, viewer_role: role }} me={me}>
      <AssistantControlsCard />
    </BusinessProvider>,
    { locale },
  );
}

describe("AssistantControlsCard: an owner's kill switches", () => {
  beforeEach(() => {
    queryCache.clear();
    vi.mocked(api.GET).mockReset();
    vi.mocked(api.PUT).mockReset();
  });

  it.each(["en", "it"] as const)("lists the hand-over and every action, in %s", async (locale) => {
    const { t } = textsIn(locale);
    answerGet(() => ok(stored));
    renderCard("owner", locale);

    const card = await screen.findByTestId("assistant-controls");
    expect(within(card).getByRole("switch", { name: t("assistantControls.handOver.label") })).toBeTruthy();
    const links = within(card).getByRole("switch", { name: t("assistantControls.actions.send_link") });
    expect(links.getAttribute("aria-checked")).toBe("false");
    const bookings = within(card).getByRole("switch", { name: t("assistantControls.actions.create_booking") });
    expect(bookings.getAttribute("aria-checked")).toBe("true");
  });

  it("hands every customer to the team, keeping the memory switches as stored", async () => {
    const user = userEvent.setup();
    const { t } = textsIn("en");
    answerGet(() => ok(stored));
    vi.mocked(api.PUT).mockImplementation((() => ok({ ...stored, is_paused: true })) as never);
    renderCard();

    await user.click(await screen.findByRole("switch", { name: t("assistantControls.handOver.label") }));

    expect(vi.mocked(api.PUT)).toHaveBeenCalledWith(SETTINGS, {
      params: { path: { business_id: "business_1" } },
      body: { remembers_customers: false, shares_team_notes: false, is_paused: true, disabled_tools: ["send_link"] },
    });
    expect(await screen.findByText(t("assistantControls.handedOver"))).toBeTruthy();
  });

  it("switches an action off", async () => {
    const user = userEvent.setup();
    const { t } = textsIn("en");
    answerGet(() => ok(stored));
    vi.mocked(api.PUT).mockImplementation((() => ok({ ...stored, disabled_tools: ["cancel_booking", "send_link"] })) as never);
    renderCard();

    await user.click(await screen.findByRole("switch", { name: t("assistantControls.actions.cancel_booking") }));

    expect(vi.mocked(api.PUT)).toHaveBeenCalledWith(SETTINGS, {
      params: { path: { business_id: "business_1" } },
      body: { remembers_customers: false, shares_team_notes: false, is_paused: false, disabled_tools: ["cancel_booking", "send_link"] },
    });
  });

  it("shows staff the switches without letting them change them", async () => {
    const { t } = textsIn("en");
    answerGet(() => ok(stored));
    renderCard("staff");

    const handOver = await screen.findByRole("switch", { name: t("assistantControls.handOver.label") });
    expect(handOver).toHaveProperty("disabled", true);
    expect(screen.getByText(t("assistantControls.ownerOnly"))).toBeTruthy();
  });
});

import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import type { BusinessClosureView, BusinessView, CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { answerGet, ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { CloseBusinessCard } from "./CloseBusinessCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() } }));
const refresh = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({ usePathname: () => "/b/business_1/settings", useRouter: () => ({ refresh }) }));

const CLOSURE = "/v1/businesses/{business_id}/closure";
const DAY_MS = 24 * 60 * 60 * 1000;
const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;
const business = {
  id: "business_1",
  name: "Café Tbilisi",
  status: "live",
  viewer_role: "owner",
  timezone: "Asia/Tbilisi",
  currency_code: "GEL",
} as unknown as BusinessView;
const open: BusinessClosureView = { business_id: "business_1", state: "active", can_cancel: false, viewer_is_owner: true };

function closing(changes: Partial<BusinessClosureView> = {}): BusinessClosureView {
  const now = Date.now();
  return {
    business_id: "business_1",
    state: "pending_deletion",
    reason: "owner_request",
    requested_at: now * 1000,
    delete_after: (now + 30 * DAY_MS - 60_000) * 1000,
    actor_name: "Nino",
    can_cancel: true,
    viewer_is_owner: true,
    ...changes,
  };
}

function renderCard(role: "owner" | "staff" = "owner", locale: "en" | "it" = "en") {
  return renderInLocale(
    <BusinessProvider business={{ ...business, viewer_role: role }} me={me}>
      <CloseBusinessCard />
    </BusinessProvider>,
    { locale },
  );
}

describe("CloseBusinessCard: Settings → Business, the danger zone", () => {
  beforeEach(() => {
    queryCache.clear();
    vi.mocked(api.GET).mockReset();
    vi.mocked(api.POST).mockReset();
    vi.mocked(api.DELETE).mockReset();
    refresh.mockReset();
  });

  it.each(["en", "it"] as const)("says what closing does and offers the export first, in %s", async (locale) => {
    const { t } = textsIn(locale);
    answerGet(() => ok(open));
    renderCard("owner", locale);

    const card = await screen.findByTestId("close-business");
    for (const key of ["closure.zone.willPause", "closure.zone.willStopCharges", "closure.zone.willDelete", "closure.zone.willKeep"] as const) {
      expect(card.textContent).toContain(t(key));
    }
    const exportLink = within(card).getByRole("link", { name: t("closure.zone.export") });
    expect(exportLink.getAttribute("href")).toBe("/b/business_1/settings/privacy");
  });

  it("closes only once the business's name is typed, and sends it", async () => {
    const user = userEvent.setup();
    const { t } = textsIn("en");
    answerGet(() => ok(open));
    vi.mocked(api.POST).mockImplementation((() => ok(closing())) as never);
    renderCard();

    await user.click(await screen.findByRole("button", { name: t("closure.zone.action") }));
    const dialog = screen.getByRole("dialog", { name: t("closure.zone.dialogTitle") });
    const confirm = within(dialog).getByRole("button", { name: t("closure.zone.confirm") });
    expect(confirm).toHaveProperty("disabled", true);
    await user.type(within(dialog).getByRole("textbox"), "café tbilisi ");
    expect(confirm).toHaveProperty("disabled", false);
    await user.click(confirm);

    expect(vi.mocked(api.POST)).toHaveBeenCalledWith(CLOSURE, {
      params: { path: { business_id: "business_1" } },
      body: { confirmation_name: "Café Tbilisi" },
    });
    expect(await screen.findByRole("heading", { name: t("closure.zone.pendingTitle") })).toBeTruthy();
    expect(refresh).toHaveBeenCalled();
  });

  it("while closing, says who closed it and keeps it on request", async () => {
    const user = userEvent.setup();
    const { t } = textsIn("en");
    let view = closing();
    answerGet(() => ok(view));
    vi.mocked(api.DELETE).mockImplementation((() => {
      view = { ...open };
      return Promise.resolve({ data: undefined, response: new Response(null, { status: 204 }) });
    }) as never);
    renderCard();

    const card = await screen.findByTestId("close-business");
    expect(card.textContent).toContain("Nino");
    expect(card.textContent).toContain(t("closure.zone.keepHint"));
    await user.click(within(card).getByRole("button", { name: t("closure.zone.keep") }));

    expect(vi.mocked(api.DELETE)).toHaveBeenCalledWith(CLOSURE, { params: { path: { business_id: "business_1" } } });
    expect(await screen.findByRole("button", { name: t("closure.zone.action") })).toBeTruthy();
  });

  it("points to Billing when the closure for non-payment waits for a payment", async () => {
    const { t } = textsIn("en");
    answerGet(() => ok(closing({ reason: "unpaid_subscription", actor_name: null, can_cancel: false })));
    renderCard();

    const card = await screen.findByTestId("close-business");
    expect(card.textContent).toContain(t("closure.zone.unpaidHint"));
    expect(within(card).getByRole("link", { name: t("closure.zone.billing") }).getAttribute("href")).toBe(
      "/b/business_1/settings/billing",
    );
    expect(within(card).queryByRole("button", { name: t("closure.zone.keep") })).toBeNull();
  });

  it("is the owners' alone", async () => {
    answerGet(() => ok({ ...open, viewer_is_owner: false }));
    renderCard("staff");

    await waitFor(() => expect(vi.mocked(api.GET)).toHaveBeenCalled());
    expect(screen.queryByTestId("close-business")).toBeNull();
  });
});

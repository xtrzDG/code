import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import type { BusinessClosureView, BusinessView, CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { formatDate } from "@/lib/format";
import { answerGet, ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { ClosureBanner } from "./ClosureBanner";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() } }));
const pathname = vi.hoisted(() => ({ current: "/b/business_1/bookings" }));
const refresh = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({ usePathname: () => pathname.current, useRouter: () => ({ refresh }) }));

const CLOSURE = "/v1/businesses/{business_id}/closure";
const DAY_MS = 24 * 60 * 60 * 1000;
const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;
const business = {
  id: "business_1",
  name: "Café Tbilisi",
  status: "paused",
  viewer_role: "owner",
  timezone: "Asia/Tbilisi",
  currency_code: "GEL",
} as unknown as BusinessView;

function closing(days: number, changes: Partial<BusinessClosureView> = {}): BusinessClosureView {
  const now = Date.now();
  return {
    business_id: "business_1",
    state: "pending_deletion",
    reason: "owner_request",
    requested_at: (now - DAY_MS) * 1000,
    // Just under whole days, so the count does not depend on the test's own speed.
    delete_after: (now + days * DAY_MS - 60_000) * 1000,
    actor_name: "Nino",
    can_cancel: true,
    viewer_is_owner: true,
    ...changes,
  };
}

function renderBanner(role: "owner" | "staff" = "owner", locale: "en" | "ru" | "ka" | "he" | "de" = "en") {
  return renderInLocale(
    <BusinessProvider business={{ ...business, viewer_role: role }} me={me}>
      <ClosureBanner />
    </BusinessProvider>,
    { locale },
  );
}

describe("ClosureBanner: a closing business counts down to its deletion", () => {
  beforeEach(() => {
    queryCache.clear();
    pathname.current = "/b/business_1/bookings";
    vi.mocked(api.GET).mockReset();
    vi.mocked(api.DELETE).mockReset();
    refresh.mockReset();
  });

  it.each(["en", "ru", "ka", "he", "de"] as const)("says when everything is deleted, in %s", async (locale) => {
    const { t, tp } = textsIn(locale);
    const view = closing(12);
    answerGet((path) => {
      expect(path).toBe(CLOSURE);
      return ok(view);
    });
    renderBanner("owner", locale);

    const banner = await screen.findByRole("region", { name: t("closure.banner.title") });
    const date = formatDate(view.delete_after ?? 0, { locale, timeZone: "Asia/Tbilisi" });
    expect(banner.textContent).toContain(tp("closure.banner.countdown", 12, { count: "12", date }));
    expect(screen.getByRole("button", { name: t("closure.banner.keep") })).toBeTruthy();
    expect(screen.getByRole("link", { name: t("closure.banner.open") }).getAttribute("href")).toBe("/b/business_1/settings");
  });

  it("keeps the business with one tap and loads the page again", async () => {
    const { t } = textsIn("en");
    let view: BusinessClosureView = closing(20);
    answerGet(() => ok(view));
    vi.mocked(api.DELETE).mockImplementation((() => {
      view = { business_id: "business_1", state: "active" };
      return Promise.resolve({ data: undefined, response: new Response(null, { status: 204 }) });
    }) as never);
    renderBanner();

    await userEvent.click(await screen.findByRole("button", { name: t("closure.banner.keep") }));

    expect(vi.mocked(api.DELETE)).toHaveBeenCalledWith(CLOSURE, { params: { path: { business_id: "business_1" } } });
    await waitFor(() => expect(screen.queryByTestId("closure-banner")).toBeNull());
    expect(refresh).toHaveBeenCalled();
  });

  it("sends the owner to Billing when it was closed for non-payment", async () => {
    const { t } = textsIn("en");
    answerGet(() => ok(closing(5, { reason: "unpaid_subscription", actor_name: null, can_cancel: false })));
    renderBanner();

    const pay = await screen.findByRole("link", { name: t("closure.banner.pay") });
    expect(pay.getAttribute("href")).toBe("/b/business_1/settings/billing");
    expect(screen.getByText(t("closure.banner.unpaid"))).toBeTruthy();
    expect(screen.queryByRole("button", { name: t("closure.banner.keep") })).toBeNull();
  });

  it("tells staff, without the owner's actions", async () => {
    const { t } = textsIn("en");
    answerGet(() => ok(closing(9, { can_cancel: false, viewer_is_owner: false })));
    renderBanner("staff");

    await screen.findByRole("region", { name: t("closure.banner.title") });
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("says once the deletion has begun, and nothing for an open business", async () => {
    const { t } = textsIn("en");
    answerGet(() => ok({ business_id: "business_1", state: "deleting" }));
    const { unmount } = renderBanner();

    expect(await screen.findByText(t("closure.banner.deleting"))).toBeTruthy();
    unmount();
    queryCache.clear();
    answerGet(() => ok({ business_id: "business_1", state: "active" }));
    renderBanner();
    await waitFor(() => expect(vi.mocked(api.GET)).toHaveBeenCalledTimes(2));
    expect(screen.queryByTestId("closure-banner")).toBeNull();
  });

  it("leaves Settings → Business to its danger zone", async () => {
    pathname.current = "/b/business_1/settings";
    answerGet(() => ok(closing(3)));
    renderBanner();

    await waitFor(() => expect(vi.mocked(api.GET)).toHaveBeenCalled());
    expect(screen.queryByTestId("closure-banner")).toBeNull();
  });
});

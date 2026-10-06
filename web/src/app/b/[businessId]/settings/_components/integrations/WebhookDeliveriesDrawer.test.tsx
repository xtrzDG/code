import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import type { CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { answerGet, ok, pending } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { business } from "../../_lib/settingsFixtures";
import { delivery, endpoint } from "./webhookFixtures";
import { WebhookDeliveriesDrawer } from "./WebhookDeliveriesDrawer";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const DELIVERIES = "/v1/businesses/{business_id}/webhooks/{webhook_id}/deliveries";
const DELIVERY = "/v1/businesses/{business_id}/webhook-deliveries/{delivery_id}";
const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;

function renderDrawer(locale: "en" | "ru" | "ka" = "en") {
  return renderInLocale(
    <BusinessProvider business={business} me={me}>
      <WebhookDeliveriesDrawer endpoint={endpoint()} onClose={() => undefined} />
    </BusinessProvider>,
    { locale },
  );
}

const failed = delivery({
  id: "webhook_delivery_2",
  event_type: "lead.created",
  status: "failed",
  attempts: 9,
  last_status_code: 500,
  last_problem: "http_status",
});
const waiting = delivery({ id: "webhook_delivery_3", status: "pending", next_attempt_at: Date.UTC(2026, 9, 6, 10) * 1000, attempts: 2 });

describe("WebhookDeliveriesDrawer: what was sent to a webhook", () => {
  beforeEach(() => {
    queryCache.clear();
    vi.mocked(api.POST).mockReset();
  });

  it.each(["en", "ru", "ka"] as const)("lists deliveries with their state and last answer in %s", async (locale) => {
    const { t, tp } = textsIn(locale);
    answerGet((path) => (path === DELIVERIES ? ok({ items: [delivery(), failed, waiting], next_cursor: null }) : pending()));
    renderDrawer(locale);

    expect(await screen.findByText(t("apiIntegrations.deliveries.problems.http_status"))).toBeTruthy();
    expect(screen.getByText(new RegExp(tp("apiIntegrations.deliveries.attempts", 9)))).toBeTruthy();
    expect(screen.getByText(new RegExp(t("apiIntegrations.deliveries.httpStatus", { code: 500 })))).toBeTruthy();
    expect(screen.getAllByText(t("apiIntegrations.deliveries.statuses.pending")).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: t("apiIntegrations.deliveries.retry") })).toHaveLength(1);
  });

  it("says nothing was sent yet", async () => {
    const { t } = textsIn("en");
    answerGet((path) => (path === DELIVERIES ? ok({ items: [] }) : pending()));
    renderDrawer();
    expect(await screen.findByText(t("apiIntegrations.deliveries.empty"))).toBeTruthy();
  });

  it("shows the request body on demand and sends a failed delivery again", async () => {
    const { t } = textsIn("en");
    const user = userEvent.setup();
    answerGet((path) =>
      path === DELIVERIES
        ? ok({ items: [failed], next_cursor: "next" })
        : path === DELIVERY
          ? ok({ delivery: failed, payload: '{"id":"event_2","type":"lead.created"}' })
          : pending(),
    );
    vi.mocked(api.POST).mockImplementation((() => ok({ ...failed, status: "pending", attempts: 9 })) as never);
    renderDrawer();

    const row = (await screen.findByText(t("apiIntegrations.deliveries.problems.http_status"))).closest("li");
    if (!row) throw new Error("the failed delivery is listed");
    expect(vi.mocked(api.GET).mock.calls.some(([path]) => path === DELIVERY)).toBe(false);
    await user.click(within(row).getByRole("button", { name: t("apiIntegrations.deliveries.showBody") }));
    const body = await screen.findByLabelText(t("apiIntegrations.deliveries.body"));
    expect(body.textContent).toContain('"type": "lead.created"');

    await user.click(within(row).getByRole("button", { name: t("apiIntegrations.deliveries.retry") }));
    expect(await screen.findByText(t("apiIntegrations.deliveries.retried"))).toBeTruthy();
    const [path] = vi.mocked(api.POST).mock.calls[0] as unknown as [string];
    expect(path).toBe(`${DELIVERY}/retry`);
    expect(screen.getByRole("button", { name: t("apiIntegrations.deliveries.more") })).toBeTruthy();
  });
});

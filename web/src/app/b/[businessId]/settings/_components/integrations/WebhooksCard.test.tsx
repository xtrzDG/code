import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import type { CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { answerGet, failure, ok, pending } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { business } from "../../_lib/settingsFixtures";
import { endpoint, endpointList, SECRET, delivery } from "./webhookFixtures";
import { WebhooksCard } from "./WebhooksCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const WEBHOOKS = "/v1/businesses/{business_id}/webhooks";
const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;
const { t, tp } = textsIn("en");

function renderCard(locale: "en" | "ru" | "ka" = "en") {
  return renderInLocale(
    <BusinessProvider business={business} me={me}>
      <WebhooksCard />
    </BusinessProvider>,
    { locale },
  );
}

async function rowOf(name: string) {
  const row = (await screen.findByText(name)).closest("li");
  if (!row) throw new Error(`the row of ${name} is listed`);
  return row;
}

async function choose(row: HTMLElement, action: string) {
  const user = userEvent.setup();
  await user.click(within(row).getByRole("button", { name: t("apiIntegrations.webhooks.actions.menu") }));
  await user.click(screen.getByRole("menuitem", { name: action }));
}

describe("WebhooksCard: where the business's events go", () => {
  beforeEach(() => {
    queryCache.clear();
    for (const method of [api.POST, api.PATCH, api.DELETE]) vi.mocked(method).mockReset();
  });

  it.each(["en", "ru", "ka"] as const)("lists each webhook with its state and events in %s", async (locale) => {
    const texts = textsIn(locale);
    const off = endpoint({ id: "webhook_2", label: "Zapier", status: "disabled", origin: "api", disabled_at: 1, consecutive_failures: 15 });
    answerGet((path) => (path === WEBHOOKS ? ok(endpointList([endpoint({ consecutive_failures: 2 }), off])) : pending()));
    renderCard(locale);

    const crm = await rowOf("CRM");
    expect(within(crm).getByText(texts.t("apiIntegrations.webhooks.statuses.active"))).toBeTruthy();
    expect(within(crm).getByText(texts.tp("apiIntegrations.webhooks.failures", 2))).toBeTruthy();
    expect(within(crm).getByText(new RegExp(texts.t("apiIntegrations.events.lead_created")))).toBeTruthy();
    const zapier = await rowOf("Zapier");
    expect(within(zapier).getByText(texts.t("apiIntegrations.webhooks.statuses.disabled"))).toBeTruthy();
    expect(within(zapier).getByText(texts.t("apiIntegrations.webhooks.origins.api"))).toBeTruthy();
    expect(screen.getByText(texts.t("apiIntegrations.webhooks.limits", { count: 10, failures: 15 }))).toBeTruthy();
  });

  it("adds a webhook with its events and shows its signing secret once", async () => {
    const user = userEvent.setup();
    answerGet((path) => (path === WEBHOOKS ? ok(endpointList([])) : pending()));
    const created = endpoint({ id: "webhook_9", label: null, url: "https://hooks.example.com/in", event_types: ["booking.cancelled"] });
    vi.mocked(api.POST).mockImplementation((() => ok({ endpoint: created, signing_secret: SECRET })) as never);
    renderCard();

    expect(await screen.findByText(t("apiIntegrations.webhooks.empty"))).toBeTruthy();
    await user.click(screen.getByRole("button", { name: t("apiIntegrations.webhooks.add") }));
    await user.type(screen.getByLabelText(t("apiIntegrations.webhooks.dialog.url"), { exact: false }), "https://hooks.example.com/in");
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: t("apiIntegrations.webhooks.dialog.create") }));
    expect(screen.getByText(t("apiIntegrations.webhooks.dialog.eventsMissing"))).toBeTruthy();
    expect(api.POST).not.toHaveBeenCalled();

    await user.click(screen.getByLabelText(t("apiIntegrations.events.booking_cancelled")));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: t("apiIntegrations.webhooks.dialog.create") }));
    const [path, init] = vi.mocked(api.POST).mock.calls[0] as unknown as [string, { body: unknown }];
    expect(path).toBe(WEBHOOKS);
    expect(init.body).toEqual({ url: "https://hooks.example.com/in", label: null, event_types: ["booking.cancelled"] });
    expect(await screen.findByText(SECRET)).toBeTruthy();
    expect(screen.getByText(t("apiIntegrations.secret.webhookDescription"))).toBeTruthy();
    expect(screen.getByText("https://hooks.example.com/in")).toBeTruthy();
  });

  it("explains an address that cannot receive webhooks", async () => {
    const user = userEvent.setup();
    answerGet((path) => (path === WEBHOOKS ? ok(endpointList([])) : pending()));
    vi.mocked(api.POST).mockImplementation((() =>
      failure(422, {
        error: "validation_failed",
        message: "Not public",
        reasons: [{ code: "not_public", message: "Not public", details: ["not_public"] }],
      })) as never);
    renderCard();

    await user.click(await screen.findByRole("button", { name: t("apiIntegrations.webhooks.add") }));
    await user.type(screen.getByLabelText(t("apiIntegrations.webhooks.dialog.url"), { exact: false }), "https://10.0.0.7/in");
    await user.click(screen.getByLabelText(t("apiIntegrations.events.lead_created")));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: t("apiIntegrations.webhooks.dialog.create") }));
    expect(await screen.findByText(t("apiIntegrations.webhooks.reasons.not_public"))).toBeTruthy();
  });

  it("sends a test event, pauses, replaces the secret and deletes", async () => {
    answerGet((path) => (path === WEBHOOKS ? ok(endpointList([endpoint()])) : pending()));
    vi.mocked(api.POST).mockImplementation(((path: string) =>
      path.endsWith("/test")
        ? ok(delivery({ id: "webhook_delivery_9", is_test: true, event_type: "webhook.test" }))
        : ok({ endpoint: endpoint({ secret_hint: "zz99" }), signing_secret: SECRET })) as never);
    vi.mocked(api.PATCH).mockImplementation((() => ok(endpoint({ status: "paused" }))) as never);
    vi.mocked(api.DELETE).mockImplementation((() => ok(undefined)) as never);
    const user = userEvent.setup();
    renderCard();

    await choose(await rowOf("CRM"), t("apiIntegrations.webhooks.actions.test"));
    expect(await screen.findByText(t("apiIntegrations.webhooks.toasts.testDelivered"))).toBeTruthy();

    await choose(await rowOf("CRM"), t("apiIntegrations.webhooks.actions.pause"));
    const [, patch] = vi.mocked(api.PATCH).mock.calls[0] as unknown as [string, { body: unknown }];
    expect(patch.body).toEqual({ status: "paused" });
    expect(await screen.findByText(t("apiIntegrations.webhooks.statuses.paused"))).toBeTruthy();

    await choose(await rowOf("CRM"), t("apiIntegrations.webhooks.actions.rotate"));
    await user.click(screen.getByRole("button", { name: t("apiIntegrations.webhooks.rotateDialog.confirm") }));
    expect(await screen.findByText(SECRET)).toBeTruthy();
    await user.click(screen.getByRole("button", { name: t("apiIntegrations.secret.done") }));

    await choose(await rowOf("CRM"), t("apiIntegrations.webhooks.actions.delete"));
    await user.click(screen.getByRole("button", { name: t("apiIntegrations.webhooks.deleteDialog.confirm") }));
    expect(await screen.findByText(t("apiIntegrations.webhooks.empty"))).toBeTruthy();
    expect(tp("apiIntegrations.webhooks.eventCount", 2)).toBeTruthy();
  });
});

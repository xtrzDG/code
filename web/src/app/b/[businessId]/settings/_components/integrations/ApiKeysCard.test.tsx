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
import { ApiKeysCard } from "./ApiKeysCard";
import { apiKeyList, TOKEN } from "./webhookFixtures";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const KEYS = "/v1/businesses/{business_id}/api-keys";
const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;
const { t, tp } = textsIn("en");

function renderCard(locale: "en" | "ru" | "ka" = "en") {
  return renderInLocale(
    <BusinessProvider business={business} me={me}>
      <ApiKeysCard />
    </BusinessProvider>,
    { locale },
  );
}

describe("ApiKeysCard: keys of Zapier and the public API", () => {
  beforeEach(() => {
    queryCache.clear();
    vi.mocked(api.POST).mockReset();
    vi.mocked(api.DELETE).mockReset();
  });

  it.each(["en", "ru", "ka"] as const)("lists keys by prefix with their scopes, never a secret, in %s", async (locale) => {
    const texts = textsIn(locale);
    answerGet((path) => (path === KEYS ? ok(apiKeyList()) : pending()));
    renderCard(locale);

    const zapier = (await screen.findByText("Zapier")).closest("li");
    if (!zapier) throw new Error("the Zapier key is listed");
    expect(within(zapier).getByText("awk_aaaaaaaa_…")).toBeTruthy();
    expect(within(zapier).getByText(new RegExp(texts.t("apiIntegrations.apiKeys.scopes.webhooks_manage").replace(/[()]/g, ".")))).toBeTruthy();
    const old = (await screen.findByText("Old script")).closest("li");
    if (!old) throw new Error("the revoked key is listed");
    expect(within(old).getByText(texts.t("apiIntegrations.apiKeys.statuses.revoked"))).toBeTruthy();
    expect(within(old).queryByRole("button")).toBeNull();
    const limits = `${texts.tp("apiIntegrations.apiKeys.limits", 10)} ${texts.tp("apiIntegrations.apiKeys.rate", 120, { rate: 120 })}`;
    expect(screen.getByText(limits)).toBeTruthy();
    if (locale === "en") {
      expect(limits).toBe("Up to 10 active keys. A key makes up to 120 requests a minute.");
    }
  });

  it("creates a key with chosen scopes and shows its token once", async () => {
    const user = userEvent.setup();
    answerGet((path) => (path === KEYS ? ok(apiKeyList({ items: [] })) : pending()));
    const created = { id: "api_key_9", name: "CRM", prefix: "awk_cccccccc", scopes: ["leads:write"], status: "active", created_at: 1 };
    vi.mocked(api.POST).mockImplementation((() => ok({ api_key: created, token: TOKEN })) as never);
    renderCard();

    expect(await screen.findByText(t("apiIntegrations.apiKeys.empty"))).toBeTruthy();
    await user.click(screen.getByRole("button", { name: t("apiIntegrations.apiKeys.add") }));
    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText(t("apiIntegrations.apiKeys.dialog.name"), { exact: false }), "CRM");
    await user.click(within(dialog).getByRole("button", { name: t("apiIntegrations.apiKeys.dialog.create") }));
    expect(within(dialog).getByText(t("apiIntegrations.apiKeys.dialog.scopesMissing"))).toBeTruthy();
    await user.click(within(dialog).getByLabelText(new RegExp(t("apiIntegrations.apiKeys.scopes.leads_write"))));
    await user.click(within(dialog).getByRole("button", { name: t("apiIntegrations.apiKeys.dialog.create") }));

    const [, init] = vi.mocked(api.POST).mock.calls[0] as unknown as [string, { body: unknown }];
    expect(init.body).toEqual({ name: "CRM", scopes: ["leads:write"] });
    expect(await screen.findByText(TOKEN)).toBeTruthy();
    expect(screen.getByText(t("apiIntegrations.secret.apiKeyDescription"))).toBeTruthy();
    await user.click(screen.getByRole("button", { name: t("apiIntegrations.secret.done") }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByText("CRM")).toBeTruthy();
  });

  it("explains the key limit", async () => {
    const user = userEvent.setup();
    answerGet((path) => (path === KEYS ? ok(apiKeyList({ items: [] })) : pending()));
    vi.mocked(api.POST).mockImplementation((() =>
      failure(409, { error: "conflict", message: "Too many", reasons: [{ code: "api_key_limit_reached", message: "Too many", details: ["10"] }] })) as never);
    renderCard();

    await user.click(await screen.findByRole("button", { name: t("apiIntegrations.apiKeys.add") }));
    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText(t("apiIntegrations.apiKeys.dialog.name"), { exact: false }), "CRM");
    await user.click(within(dialog).getByLabelText(new RegExp(t("apiIntegrations.apiKeys.scopes.leads_read"))));
    await user.click(within(dialog).getByRole("button", { name: t("apiIntegrations.apiKeys.dialog.create") }));
    expect(await screen.findByText(tp("apiIntegrations.apiKeys.reasons.api_key_limit_reached", 10))).toBeTruthy();
  });

  it("revokes a key after asking", async () => {
    const user = userEvent.setup();
    answerGet((path) => (path === KEYS ? ok(apiKeyList()) : pending()));
    vi.mocked(api.DELETE).mockImplementation((() => ok(undefined)) as never);
    renderCard();

    const zapier = (await screen.findByText("Zapier")).closest("li");
    if (!zapier) throw new Error("the Zapier key is listed");
    await user.click(within(zapier).getByRole("button", { name: t("apiIntegrations.apiKeys.revoke") }));
    expect(screen.getByText(t("apiIntegrations.apiKeys.revokeDialog.title", { name: "Zapier" }))).toBeTruthy();
    await user.click(screen.getByRole("button", { name: t("apiIntegrations.apiKeys.revokeDialog.confirm") }));
    expect(await screen.findByText(t("apiIntegrations.apiKeys.toasts.revoked"))).toBeTruthy();
    const [path, init] = vi.mocked(api.DELETE).mock.calls[0] as unknown as [string, { params: { path: Record<string, string> } }];
    expect(path).toBe(`${KEYS}/{api_key_id}`);
    expect(init.params.path.api_key_id).toBe("api_key_1");
  });
});

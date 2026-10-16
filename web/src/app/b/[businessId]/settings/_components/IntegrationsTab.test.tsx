import { screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { queryCache } from "@/api/queryCache";
import type { CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import type { IntegrationView, ResourceSyncSummary } from "@/lib/resourceCalendar";
import { answerGet, ok, pending } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { business } from "../_lib/settingsFixtures";
import { IntegrationsTab } from "./IntegrationsTab";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const INTEGRATIONS = "/v1/businesses/{business_id}/integrations";
const RESOURCES = "/v1/businesses/{business_id}/resources";
const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;

const items: IntegrationView[] = [
  { kind: "google_calendar", state: "off", resource_count: 0, attention_count: 0 },
  { kind: "ical_import", state: "attention", resource_count: 2, attention_count: 1, last_synced_at: Date.UTC(2026, 9, 6, 8) * 1000 },
  { kind: "ical_export", state: "on", resource_count: 1, attention_count: 0 },
  { kind: "cal_com", state: "off", resource_count: 0, attention_count: 0 },
];
const resources: ResourceSyncSummary[] = [
  { resource_id: "resource_1", source_count: 2, problem_count: 1, is_export_on: true },
  { resource_id: "resource_gone", source_count: 1, problem_count: 0, is_export_on: false },
];

function serve(summaries: ResourceSyncSummary[], names: "loaded" | "loading" = "loaded") {
  answerGet((path) => {
    if (path === INTEGRATIONS) return ok({ items, resources: summaries });
    if (path === RESOURCES) return names === "loaded" ? ok({ items: [{ id: "resource_1", name: "Sea view" }] }) : pending();
    return pending();
  });
}

function renderTab(locale: "en" | "ru" | "ka" = "en") {
  return renderInLocale(
    <BusinessProvider business={business} me={me}>
      <IntegrationsTab />
    </BusinessProvider>,
    { locale },
  );
}

describe("IntegrationsTab: the business's calendars and booking systems", () => {
  beforeEach(() => {
    queryCache.clear();
  });

  it.each(["en", "ru", "ka"] as const)("lists every integration with its state in %s", async (locale) => {
    const { t, tp } = textsIn(locale);
    serve(resources);
    renderTab(locale);

    const imports = (await screen.findByText(t("calendarSync.integrations.kinds.ical_import"))).closest("li");
    if (!imports) throw new Error("the iCal import row is listed");
    expect(within(imports).getByText(t("calendarSync.integrations.states.attention"))).toBeTruthy();
    expect(within(imports).getByText(tp("calendarSync.integrations.attention", 1))).toBeTruthy();
    expect(within(imports).getByText(tp("calendarSync.integrations.resources", 2), { exact: false })).toBeTruthy();
    expect(screen.getByText(t("calendarSync.integrations.kinds.cal_com"))).toBeTruthy();
    const connect = screen.getByRole("link", { name: t("calendarSync.integrations.connectGoogle") });
    expect(connect.getAttribute("href")).toBe(`/b/${business.id}/assistant/channels`);
  });

  it("names the resources with calendars, problems first, and a removed one as such", async () => {
    const { t, tp } = textsIn("en");
    serve(resources);
    renderTab();

    expect(await screen.findByText("Sea view")).toBeTruthy();
    expect(screen.getByText(tp("calendarSync.row.problems", 1))).toBeTruthy();
    expect(screen.getByText(t("calendarSync.integrations.removedResource"))).toBeTruthy();
    expect(screen.getByText(tp("calendarSync.row.sources", 1))).toBeTruthy();
    const manage = screen.getByRole("link", { name: t("calendarSync.integrations.manage") });
    expect(manage.getAttribute("href")).toBe(`/b/${business.id}/assistant/knowledge/resources`);
  });

  it("says no resource has calendars yet, and waits for names without calling them removed", async () => {
    const { t } = textsIn("en");
    serve([]);
    const first = renderTab();
    expect(await screen.findByText(t("calendarSync.integrations.noResources"))).toBeTruthy();
    first.unmount();

    queryCache.clear();
    serve(resources, "loading");
    renderTab();
    expect(await screen.findByText(t("calendarSync.integrations.kinds.google_calendar"))).toBeTruthy();
    expect(screen.queryByText(t("calendarSync.integrations.removedResource"))).toBeNull();
  });
});

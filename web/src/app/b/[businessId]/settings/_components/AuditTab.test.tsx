import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { queryCache } from "@/api/queryCache";
import type { CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { answerGet, failure, lastGetQuery, ok, pending } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import type { AuditLogEntry, AuditLogPage } from "../_lib/audit";
import { business } from "../_lib/settingsFixtures";
import { AuditTab } from "./AuditTab";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const AUDIT_LOG = "/v1/businesses/{business_id}/audit-log";
const { t } = textsIn("en");
const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;

const entry: AuditLogEntry = {
  id: "audit_1",
  action: "export",
  entity: "booking",
  entity_id: "booking_7",
  actor_id: "user_owner",
  ip_address: "203.0.113.7",
  occurred_at: Date.UTC(2026, 9, 1, 9, 30) * 1000,
  record_count: 12,
};

function page(items: AuditLogEntry[]): AuditLogPage {
  return { items, next_cursor: null, entities: ["booking"], actor_ids: ["user_owner"] };
}

function renderTab() {
  return renderInLocale(
    <BusinessProvider business={business} me={me}>
      <AuditTab />
    </BusinessProvider>,
  );
}

describe("AuditTab: the audit log table and its states", () => {
  beforeEach(() => {
    queryCache.clear();
  });

  it("shows a busy loading region, and no table, while the first page loads", () => {
    answerGet(() => pending());
    renderTab();

    const loading = screen.getByRole("status");
    expect(loading.getAttribute("aria-busy")).toBe("true");
    expect(within(loading).getByText(t("common.loading"))).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("explains a failed load with its request id and loads again on Retry", async () => {
    const user = userEvent.setup();
    answerGet(() => failure(500, { error: "internal_error", message: "database away" }, "req_audit_9"));
    renderTab();

    expect(await screen.findByText(t("errors.codes.internal_error"))).toBeTruthy();
    expect(screen.getByText(t("common.requestId", { id: "req_audit_9" }))).toBeTruthy();
    expect(screen.queryByText(/database away/)).toBeNull();
    expect(screen.queryByRole("table")).toBeNull();

    answerGet(() => ok(page([entry])));
    await user.click(screen.getByRole("button", { name: t("common.retry") }));

    expect(await screen.findByRole("table", { name: t("settings.audit.title") })).toBeTruthy();
    expect(screen.queryByText(t("errors.codes.internal_error"))).toBeNull();
  });

  it("says the log is empty, and differently when filters hide everything", async () => {
    const user = userEvent.setup();
    answerGet(() => ok(page([])));
    renderTab();

    expect(await screen.findByText(t("settings.audit.empty"))).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();

    await user.selectOptions(screen.getByRole("combobox", { name: t("settings.audit.filter") }), "export");

    expect(await screen.findByText(t("settings.auditFilters.emptyFiltered"))).toBeTruthy();
    expect(lastGetQuery().action).toBe("export");
  });

  it("lists the entries in a captioned table with one header per column", async () => {
    answerGet((path) => (path === AUDIT_LOG ? ok(page([entry])) : pending()));
    renderTab();

    const table = await screen.findByRole("table", { name: t("settings.audit.title") });
    const headers = within(table)
      .getAllByRole("columnheader")
      .map((header) => header.textContent);
    expect(headers).toEqual([
      t("settings.audit.when"),
      t("settings.audit.action"),
      t("settings.audit.what"),
      t("settings.audit.who"),
      t("settings.audit.ip"),
    ]);
    const [, row] = within(table).getAllByRole("row");
    expect(row?.textContent).toContain(t("settings.audit.actions.export"));
    expect(row?.textContent).toContain("Dato");
    expect(row?.textContent).toContain("203.0.113.7");
  });
});

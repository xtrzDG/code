import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { queryCache } from "@/api/queryCache";
import { answerGet, lastGetQuery, ok, pending } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import type { AuditChainOverview, PlatformAuditEntry, PlatformAuditLogPage } from "../../_lib/audit";
import { AuditScreen } from "./AuditScreen";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const CHAINS = "/v1/admin/audit-log/chains";
const LOG = "/v1/admin/audit-log";
const CHECKED = Date.UTC(2026, 9, 12, 3, 15) * 1000;
const BUSINESS = "business_0b7f3c2a-1111-4c4c-9a91-96bb90f4b1dc";

const overview: AuditChainOverview = {
  platform: { status: "intact", verified_through_position: 88, entries_checked: 5, checked_at: CHECKED },
  intact_chains: 41,
  broken_chains: 1,
  broken: [{ business_id: BUSINESS, broken_position: 12, problem: "hash_mismatch", checked_at: CHECKED }],
};

const failed: PlatformAuditEntry = {
  id: "audit_1",
  action: "login",
  security_event: "otp_locked",
  entity: "login_destination",
  entity_id: "dest_0123456789abcdef0123456789abcdef",
  ip_address: "198.51.100.7",
  occurred_at: CHECKED,
  chain_position: 88,
};

function answers(log: PlatformAuditLogPage | Promise<never>) {
  answerGet((path) => (path === CHAINS ? ok(overview) : path === LOG ? (log instanceof Promise ? log : ok(log)) : pending()));
}

describe("AuditScreen: the tamper check and the platform's own log", () => {
  beforeEach(() => {
    queryCache.clear();
  });

  it.each(["en", "ru", "ka", "he", "de"] as const)("shows the chains and the platform's entries in %s", async (locale) => {
    const { t } = textsIn(locale);
    answers({ items: [failed], next_cursor: null });
    renderInLocale(<AuditScreen />, { locale });

    const chains = await screen.findByRole("region", { name: t("adminAudit.chains.title") });
    expect(within(chains).getByText(t("adminAudit.chains.platform"))).toBeTruthy();
    expect(within(chains).getByRole("link", { name: BUSINESS }).getAttribute("href")).toBe(`/admin/clients/${BUSINESS}`);
    expect(within(chains).getByText(new RegExp(t("auditChain.problems.hash_mismatch")))).toBeTruthy();
    const table = await screen.findByRole("table", { name: t("adminAudit.log.title") });
    expect(within(table).getByText(t("adminAudit.events.otp_locked"))).toBeTruthy();
    expect(within(table).getByText(t("adminAudit.entities.login_destination"))).toBeTruthy();
    expect(within(table).getByText("dest_01234567")).toBeTruthy();
    expect(within(table).getByText(t("adminAudit.log.unknownPerson"))).toBeTruthy();
  });

  it("filters the log by security event on the server", async () => {
    const user = userEvent.setup();
    const { t } = textsIn("en");
    answers({ items: [failed], next_cursor: null });
    renderInLocale(<AuditScreen />);

    await screen.findByRole("table", { name: t("adminAudit.log.title") });
    answers({ items: [], next_cursor: null });
    await user.selectOptions(screen.getByLabelText(t("adminAudit.log.event")), "logout");

    expect(await screen.findByText(t("adminAudit.log.emptyFiltered"))).toBeTruthy();
    expect(lastGetQuery()).toMatchObject({ security_event: "logout", limit: "50" });
  });

  it("says every log is intact when no chain is broken", async () => {
    const { t } = textsIn("en");
    answerGet((path) =>
      path === CHAINS ? ok({ ...overview, broken_chains: 0, broken: [] }) : path === LOG ? ok({ items: [], next_cursor: null }) : pending(),
    );
    renderInLocale(<AuditScreen />);

    expect(await screen.findByText(t("adminAudit.chains.allIntact"))).toBeTruthy();
    expect(await screen.findByText(t("adminAudit.log.empty"))).toBeTruthy();
  });
});

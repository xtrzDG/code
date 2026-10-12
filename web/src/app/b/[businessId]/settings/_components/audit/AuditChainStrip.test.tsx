import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { queryCache } from "@/api/queryCache";
import type { CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import type { AuditChainStatusView } from "@/lib/auditChain";
import { answerGet, failure, ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { business } from "../../_lib/settingsFixtures";
import { AuditChainStrip } from "./AuditChainStrip";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const CHAIN = "/v1/businesses/{business_id}/audit-log/chain";
const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;
const CHECKED = Date.UTC(2026, 9, 12, 3, 15) * 1000;

function answer(view: AuditChainStatusView | Promise<unknown>) {
  answerGet((path) => {
    expect(path).toBe(CHAIN);
    return view instanceof Promise ? view : ok(view);
  });
}

function renderStrip(locale: "en" | "ru" | "ka" | "he" | "de" = "en") {
  return renderInLocale(
    <BusinessProvider business={business} me={me}>
      <AuditChainStrip />
    </BusinessProvider>,
    { locale },
  );
}

describe("AuditChainStrip: the tamper check on Settings → Audit", () => {
  beforeEach(() => {
    queryCache.clear();
  });

  it.each(["en", "ru", "ka", "he", "de"] as const)("says an intact log was checked, in %s", async (locale) => {
    const { t } = textsIn(locale);
    answer({ status: "intact", verified_through_position: 214, entries_checked: 3, checked_at: CHECKED });
    renderStrip(locale);

    expect(await screen.findByText(t("auditChain.status.intact"))).toBeTruthy();
    expect(screen.getByText(t("auditChain.verdict.intact"))).toBeTruthy();
    expect(screen.getByText(new RegExp(t("auditChain.verifiedThrough", { position: "214" })))).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("names the entry and the problem of a changed log, as an alert", async () => {
    const { t } = textsIn("en");
    answer({ status: "broken", problem: "position_gap", broken_position: 17, entries_checked: 20, checked_at: CHECKED });
    renderStrip();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe(
      t("auditChain.verdict.broken", { position: "17", problem: t("auditChain.problems.position_gap") }),
    );
    expect(screen.getByText(t("auditChain.status.broken"))).toBeTruthy();
  });

  it("says when the first check has not run yet, and where a purge left off", async () => {
    const { t } = textsIn("en");
    answer({ status: null, entries_checked: 0, purged_through_position: 1200 });
    renderStrip();

    expect(await screen.findByText(t("auditChain.status.unchecked"))).toBeTruthy();
    expect(screen.getByText(t("auditChain.verdict.unchecked"))).toBeTruthy();
    expect(screen.getByText(t("auditChain.purgedThrough", { position: "1,200" }))).toBeTruthy();
  });

  it("shows nothing for a member the check is not for (the log says why)", async () => {
    answer(failure(403, { error: "access_denied", message: "owners only" }));
    const { container } = renderStrip();

    await vi.waitFor(() => expect(container.textContent).toBe(""));
  });
});

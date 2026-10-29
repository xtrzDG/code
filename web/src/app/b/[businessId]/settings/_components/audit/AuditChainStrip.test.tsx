import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

function answer(...views: (AuditChainStatusView | Promise<unknown>)[]) {
  let call = 0;
  answerGet((path) => {
    expect(path).toBe(CHAIN);
    const view = views[Math.min(call, views.length - 1)];
    call += 1;
    return view instanceof Promise ? view : ok(view);
  });
}

function renderStrip(locale: "en" | "it" = "en") {
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

  it.each(["en", "it"] as const)("says an intact log was checked, in %s", async (locale) => {
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
    // A gap is reported at the missing position: entry 17 itself is gone.
    expect(alert.textContent).toBe(
      "The daily check found a problem at entry 17: it was removed. The platform team has been alerted.",
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

  it.each(["en", "it"] as const)(
    "does not call a log with no sealed entry intact, in %s",
    async (locale) => {
      const { t } = textsIn(locale);
      answer({ status: "intact", entries_checked: 0, checked_at: CHECKED });
      renderStrip(locale);

      expect(await screen.findByText(t("auditChain.status.unsealed"))).toBeTruthy();
      expect(screen.getByText(t("auditChain.verdict.unsealed"))).toBeTruthy();
      expect(screen.queryByText(t("auditChain.status.intact"))).toBeNull();
    },
  );

  it("says a failed check could not load and loads it again on Retry", async () => {
    const { t } = textsIn("en");
    answer(
      failure(500, { error: "internal_error", message: "boom" }),
      { status: "intact", verified_through_position: 9, entries_checked: 9, checked_at: CHECKED },
    );
    renderStrip();

    await userEvent.click(await screen.findByRole("button", { name: t("common.retry") }));

    expect(await screen.findByText(t("auditChain.status.intact"))).toBeTruthy();
  });

  it("shows nothing for a member the check is not for (the log says why)", async () => {
    answer(failure(403, { error: "access_denied", message: "owners only" }));
    const { container } = renderStrip();

    await vi.waitFor(() => expect(container.textContent).toBe(""));
  });
});

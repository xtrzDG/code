import { screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { queryCache } from "@/api/queryCache";
import { answerGet, ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import type { QueuedJob } from "../../_lib/system";
import { DeadLettersCard } from "./DeadLettersCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const died: QueuedJob = {
  id: "queued_job_export",
  name: "run_business_export",
  lane: "default",
  business_id: "business_7",
  status: "dead",
  attempts: 2,
  run_at: Date.UTC(2026, 9, 6, 9, 0) * 1000,
  lease_until: null,
  last_error: "process_died: two attempts in a row ended with their worker process",
  dead_reason: "process_died",
  created_at: Date.UTC(2026, 9, 6, 8, 0) * 1000,
  updated_at: Date.UTC(2026, 9, 6, 9, 5) * 1000,
};
const failed: QueuedJob = {
  ...died,
  id: "queued_job_digest",
  name: "send_owner_digest",
  attempts: 5,
  last_error: "ExternalServiceError: provider down",
  dead_reason: "attempts_exhausted",
};

describe("DeadLettersCard: why each dead job died", () => {
  beforeEach(() => {
    queryCache.clear();
  });

  it.each(["en", "ru", "ka"] as const)("names the reason next to the error in %s", async (locale) => {
    const { t } = textsIn(locale);
    answerGet(() => ok({ items: [died, failed], next_cursor: null }));
    renderInLocale(<DeadLettersCard tallies={[]} />, { locale });

    const table = await screen.findByRole("table", { name: t("adminSystem.deadLetters.title") });
    const rows = within(table).getAllByRole("row");
    const exportRow = rows.find((row) => within(row).queryByText(died.name) !== null);
    const digestRow = rows.find((row) => within(row).queryByText(failed.name) !== null);
    if (!exportRow || !digestRow) throw new Error("both dead jobs are listed");
    expect(within(exportRow).getByText(t("adminSystem.deadLetters.reasons.process_died"))).toBeTruthy();
    expect(within(digestRow).getByText(t("adminSystem.deadLetters.reasons.attempts_exhausted"))).toBeTruthy();
    // The stored error stays in English, marked as such for screen readers.
    expect(within(digestRow).getByText(failed.last_error ?? "").getAttribute("lang")).toBe("en");
  });

  it("shows no reason for a job stored before reasons were recorded", async () => {
    const { t } = textsIn("en");
    answerGet(() => ok({ items: [{ ...failed, dead_reason: null }], next_cursor: null }));
    renderInLocale(<DeadLettersCard tallies={[]} />);

    const table = await screen.findByRole("table", { name: t("adminSystem.deadLetters.title") });
    expect(within(table).queryByText(t("adminSystem.deadLetters.reasons.attempts_exhausted"))).toBeNull();
  });
});

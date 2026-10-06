import { fireEvent, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import { answerGet, ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import type { DataTask, DataTasksView } from "../../_lib/dataTasks";
import { DataTasksCard } from "./DataTasksCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const HOUR = 3_600_000_000;
const NOW = Date.UTC(2026, 9, 6, 12, 0) * 1000;
const running: DataTask = {
  key: "backfill_lookup:contacts.last_seen_at",
  kind: "backfill_lookup",
  collection_name: "contacts",
  field: "last_seen_at",
  target_version: null,
  status: "running",
  lists: ["customers"],
  scanned_count: 5_000,
  changed_count: 4_900,
  failed_row_count: 0,
  failed_document_keys: [],
  row_estimate: 20_000,
  batch_count: 1,
  pending_since: NOW - HOUR,
  started_at: NOW - HOUR,
  last_batch_at: NOW - 60_000_000,
  finished_at: null,
  failure_count: 0,
  last_error: null,
  is_stalled: false,
};
const failed: DataTask = {
  ...running,
  key: "migrate_documents:contacts",
  kind: "migrate_documents",
  field: null,
  target_version: 4,
  status: "failed",
  failed_row_count: 2,
  failed_document_keys: ["contact_1", "contact_2"],
  pending_since: NOW - 30 * HOUR,
  is_stalled: true,
};
const done: DataTask = {
  ...running,
  key: "backfill_lookup:knowledge_items.updated_at",
  collection_name: "knowledge_items",
  field: "updated_at",
  status: "done",
  lists: ["knowledge"],
  pending_since: null,
  finished_at: NOW - HOUR,
};

function view(overrides: Partial<DataTasksView> = {}): DataTasksView {
  return {
    checked_at: NOW,
    batch_size: 5000,
    rollout: { is_settled: true, release: "4718714", other_releases: [], settles_at: null },
    open_count: 2,
    failed_count: 1,
    stalled_count: 1,
    tasks: [failed, running, done],
    ...overrides,
  };
}

describe("DataTasksCard: the post-deploy data tasks on the system page", () => {
  beforeEach(() => {
    queryCache.clear();
    vi.mocked(api.POST).mockReset();
  });

  it.each(["en", "ru", "ka"] as const)("shows each task's status, progress and lists in %s", async (locale) => {
    const { t } = textsIn(locale);
    answerGet(() => ok(view()));
    renderInLocale(<DataTasksCard />, { locale });

    const table = await screen.findByRole("table", { name: t("dataTasks.title") });
    const rows = within(table).getAllByRole("row");
    const failedRow = rows.find((row) => within(row).queryByText("contacts") !== null);
    const runningRow = rows.find((row) => within(row).queryByText("contacts.last_seen_at") !== null);
    if (!failedRow || !runningRow) throw new Error("both open tasks are listed");
    expect(within(failedRow).getByText(t("dataTasks.statuses.failed"))).toBeTruthy();
    expect(within(failedRow).getByText(t("dataTasks.isStalled"))).toBeTruthy();
    expect(within(failedRow).getByRole("button", { name: `${t("dataTasks.retry")}: contacts` })).toBeTruthy();
    expect(within(runningRow).getByRole("progressbar").getAttribute("aria-valuenow")).toBe("25");
    expect(within(runningRow).queryByRole("button")).toBeNull();
    expect(screen.getByText(t("dataTasks.settled"))).toBeTruthy();
  });

  it("says which release it waits for while the overlap lasts", async () => {
    const { t } = textsIn("en");
    answerGet(() =>
      ok(view({ rollout: { is_settled: false, release: "new", other_releases: ["old-release"], settles_at: NOW + HOUR } })),
    );
    renderInLocale(<DataTasksCard />);

    expect(await screen.findByText(/old-release/)).toBeTruthy();
    expect(screen.queryByText(t("dataTasks.settled"))).toBeNull();
  });

  it("walks a failed task again and says so", async () => {
    const { t } = textsIn("en");
    answerGet(() => ok(view()));
    vi.mocked(api.POST).mockReturnValue(ok({ task: { ...failed, status: "pending" }, audit_log_entry_id: "audit_1" }) as never);
    renderInLocale(<DataTasksCard />);

    fireEvent.click(await screen.findByRole("button", { name: `${t("dataTasks.retry")}: contacts` }));

    expect(await screen.findByText(t("dataTasks.retried"))).toBeTruthy();
    expect(vi.mocked(api.POST)).toHaveBeenCalledWith("/v1/admin/system/data-tasks/{task_key}/retry", {
      params: { path: { task_key: "migrate_documents:contacts" } },
    });
  });

  it("says when every task is done or the release has none", async () => {
    const { t } = textsIn("en");
    answerGet(() => ok(view({ open_count: 0, failed_count: 0, stalled_count: 0, tasks: [] })));
    renderInLocale(<DataTasksCard />);

    expect(await screen.findByText(t("dataTasks.allDone"))).toBeTruthy();
    expect(screen.getByText(t("dataTasks.none"))).toBeTruthy();
  });
});

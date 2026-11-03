import { waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import { answerGet, failure, ok, pending } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import type { DataTasksView } from "../../_lib/dataTasks";
import type { Incident } from "../../_lib/incidentForm";
import type { PaymentReconciliation } from "../../_lib/platformBrakes";
import type { AdminSystem, ChannelIssue, Lane, MaintenanceRun, WorkerPulse } from "../../_lib/system";
import { useSystemFolds, type SystemFolds } from "./systemFolds";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const SECOND = 1_000_000;
const NOW = 1_790_000_000 * SECOND;

function worker(overrides: Partial<WorkerPulse> = {}): WorkerPulse {
  return {
    worker_id: "worker_1",
    host_name: "srv-a",
    started_at: NOW - 3_600 * SECOND,
    beat_at: NOW,
    age_seconds: 4,
    is_stale: false,
    failing_jobs: [],
    circuits: [],
    release: "4718714c0f2e",
    ...overrides,
  };
}

function lane(overrides: Partial<Lane> = {}): Lane {
  return { lane: "inbound", waiting: 0, scheduled: 0, running: 0, dead: 0, oldest_wait_seconds: null, ...overrides };
}

const backup: MaintenanceRun = {
  kind: "backup",
  outcome: "succeeded",
  started_at: NOW - 3_600 * SECOND,
  finished_at: NOW - 3_000 * SECOND,
  archive_size: 1024,
  row_count: 10,
  release: "4718714c0f2e",
  error: null,
};

const expiring = { business_id: "business_1", channel_id: "channel_1", kind: "whatsapp", is_expired: false } as ChannelIssue;

function system(overrides: Partial<AdminSystem> = {}): AdminSystem {
  return {
    checked_at: NOW,
    workers: [worker(), worker({ worker_id: "worker_2", host_name: "srv-b" })],
    circuits: [
      { circuit: "provider:meta", state: "closed", workers_not_closed: 0, workers_reporting: 2, recent_failures: 0, opened_at: null },
    ],
    lanes: [lane({ waiting: 2 }), lane({ lane: "outbound", waiting: 1 })],
    dead_jobs: [],
    channels_in_error: [],
    channels_in_error_count: 0,
    expiring_credentials: [],
    tables: [],
    is_backup_overdue: false,
    alerts: [],
    database_bytes: 4.24 * 1024 ** 3,
    last_backup: backup,
    last_restore_drill: null,
    ...overrides,
  };
}

const matched: PaymentReconciliation = { day: "2026-11-02", ran_at: NOW, checked_count: 12, unreadable_count: 0, mismatches: [] };

/** The post-deploy data tasks after a settled deploy: every task done. */
function dataTasks(overrides: Partial<DataTasksView> = {}): DataTasksView {
  return {
    tasks: [],
    open_count: 0,
    failed_count: 0,
    stalled_count: 0,
    batch_size: 5000,
    checked_at: NOW,
    rollout: { is_settled: true, release: "4718714", other_releases: [], settles_at: null },
    ...overrides,
  };
}

/** The reconciliation and the data tasks the page's own reads answer. */
function answerReads(reconciliation: PaymentReconciliation, tasks: DataTasksView = dataTasks()) {
  answerGet((path) => (path === "/v1/admin/system/data-tasks" ? ok(tasks) : ok(reconciliation)));
}

function Probe({ data, incidents }: { data: AdminSystem; incidents?: Incident[] }) {
  const folds = useSystemFolds(data, incidents);
  return (
    <ul>
      {(Object.keys(folds) as (keyof SystemFolds)[]).map((name) => (
        <li key={name} data-fold={name}>
          {folds[name]}
        </li>
      ))}
    </ul>
  );
}

const fold = (name: keyof SystemFolds) => document.querySelector<HTMLElement>(`[data-fold="${name}"]`)!;
/** The summary's text and, when it wants a look, its colour. */
const said = (name: keyof SystemFolds) => {
  const element = fold(name);
  const tone = element.querySelector("span")?.className ?? null;
  return { text: element.textContent, tone };
};

describe("useSystemFolds: what the System page's folded rows say on a phone", () => {
  beforeEach(() => {
    queryCache.clear();
    answerReads(matched);
  });

  it.each(["en", "it"] as const)("says each healthy card's figure plainly, in %s", async (locale) => {
    const { t, tp } = textsIn(locale);
    renderInLocale(<Probe data={system()} incidents={[{ status: "resolved" } as Incident]} />, { locale });

    expect(said("workers")).toEqual({ text: tp("adminSystem.folds.live", 2), tone: null });
    expect(said("circuits")).toEqual({ text: t("adminSystem.folds.allClosed"), tone: null });
    expect(said("lanes")).toEqual({ text: tp("adminSystem.folds.due", 3), tone: null });
    expect(said("deadLetters")).toEqual({ text: t("adminSystem.folds.none"), tone: null });
    expect(said("channels")).toEqual({ text: t("adminSystem.folds.noneInError"), tone: null });
    expect(said("backups")).toEqual({ text: t("adminSystem.backups.states.ok"), tone: null });
    expect(said("database").text).toBe(t("adminSystem.bytes.gb", { value: locale === "it" ? "4,2" : "4.2" }));
    expect(said("incidents")).toEqual({ text: t("adminSystem.folds.noneOpen"), tone: null });
    await waitFor(() => expect(said("reconciliation")).toEqual({ text: t("adminSystem.folds.allMatch"), tone: null }));
    await waitFor(() => expect(said("dataTasks")).toEqual({ text: t("adminSystem.folds.noneOpen"), tone: null }));
  });

  it("colours what wants a look", async () => {
    const { t, tp } = textsIn("en");
    answerReads(
      {
        ...matched,
        mismatches: [
          {
            business_id: "business_1",
            kind: "paid_at_provider",
            payment_order_id: "payment_order_1",
            provider: "flitt",
            provider_status: "approved",
            recorded_status: "processing",
          },
        ],
      },
      dataTasks({ open_count: 3, failed_count: 1 }),
    );
    renderInLocale(
      <Probe
        data={system({
          workers: [worker(), worker({ worker_id: "worker_2", is_stale: true })],
          circuits: [
            { circuit: "provider:meta", state: "open", workers_not_closed: 2, workers_reporting: 2, recent_failures: 5, opened_at: NOW },
          ],
          lanes: [lane({ waiting: 4, dead: 1 })],
          dead_jobs: [
            { name: "send_outbound_message", count: 2 },
            { name: "record_sli", count: 1 },
          ],
          channels_in_error_count: 3,
          expiring_credentials: [expiring],
          last_backup: { ...backup, outcome: "failed" },
        })}
        incidents={[{ status: "open" } as Incident, { status: "resolved" } as Incident]}
      />,
    );

    expect(said("workers")).toEqual({ text: tp("adminSystem.folds.stale", 1), tone: "text-danger" });
    expect(said("circuits")).toEqual({ text: tp("adminSystem.folds.notClosed", 1), tone: "text-danger" });
    expect(said("lanes")).toEqual({ text: tp("adminSystem.folds.due", 4), tone: "text-danger" });
    expect(said("deadLetters")).toEqual({ text: tp("adminSystem.folds.deadJobs", 3), tone: "text-danger" });
    // A channel in error comes before a token running out.
    expect(said("channels")).toEqual({ text: tp("adminSystem.folds.inError", 3), tone: "text-danger" });
    expect(said("backups")).toEqual({ text: t("adminSystem.backups.states.failed"), tone: "text-danger" });
    expect(said("incidents")).toEqual({ text: tp("adminSystem.folds.open", 1), tone: "text-warning" });
    await waitFor(() =>
      expect(said("reconciliation")).toEqual({ text: t("platformBrakes.reconciliation.differs"), tone: "text-danger" }),
    );
    // A failed data task needs a person: it comes before the open count.
    await waitFor(() => expect(said("dataTasks")).toEqual({ text: t("dataTasks.failed", { count: "1" }), tone: "text-danger" }));
  });

  it("says how many data tasks are still open, in red once one has stalled for over a day", async () => {
    const { tp } = textsIn("en");
    answerReads(matched, dataTasks({ open_count: 2 }));
    const view = renderInLocale(<Probe data={system()} />);
    await waitFor(() => expect(said("dataTasks")).toEqual({ text: tp("dataTasks.open", 2), tone: "text-warning" }));
    view.unmount();

    queryCache.clear();
    answerReads(matched, dataTasks({ open_count: 2, stalled_count: 1 }));
    renderInLocale(<Probe data={system()} />);
    await waitFor(() => expect(said("dataTasks")).toEqual({ text: tp("dataTasks.open", 2), tone: "text-danger" }));
  });

  it("warns of tokens running out, a missing backup and a backlog", () => {
    const { t, tp } = textsIn("en");
    renderInLocale(
      <Probe
        data={system({
          lanes: [lane({ waiting: 900, oldest_wait_seconds: 3_600 })],
          expiring_credentials: [expiring, { ...expiring, channel_id: "channel_2" }],
          last_backup: null,
          workers: [],
        })}
      />,
    );
    expect(said("channels")).toEqual({ text: tp("adminSystem.folds.expiring", 2), tone: "text-warning" });
    expect(said("backups")).toEqual({ text: t("adminSystem.backups.states.missing"), tone: "text-warning" });
    expect(said("lanes")).toEqual({ text: tp("adminSystem.folds.due", 900), tone: "text-warning" });
    // No worker beats: the row says so in red.
    expect(said("workers")).toEqual({ text: t("adminSystem.folds.none"), tone: "text-danger" });
  });

  it("says nothing it does not know yet: no circuits, no lanes, an unmeasured database, incidents, a reconciliation or data tasks still loading", () => {
    answerGet(() => pending());
    renderInLocale(<Probe data={system({ circuits: [], lanes: [], database_bytes: null })} />);
    for (const name of ["circuits", "lanes", "database", "incidents", "reconciliation", "dataTasks"] as const) {
      expect(fold(name).textContent, name).toBe("");
    }
  });

  it("says nothing of the reconciliation to an admin who may not see payments, or before it first ran", async () => {
    answerGet(() => failure(403, { code: "forbidden", message: "Not allowed" }));
    const view = renderInLocale(<Probe data={system()} />);
    await waitFor(() => expect(vi.mocked(api.GET)).toHaveBeenCalledWith("/v1/admin/payments/reconciliation"));
    expect(fold("reconciliation").textContent).toBe("");
    view.unmount();

    queryCache.clear();
    answerReads({ ...matched, ran_at: null });
    renderInLocale(<Probe data={system()} />);
    await waitFor(() => expect(fold("workers").textContent).not.toBe(""));
    expect(fold("reconciliation").textContent).toBe("");
  });
});

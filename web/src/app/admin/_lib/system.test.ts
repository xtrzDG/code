import { describe, expect, it } from "vitest";

import {
  attentionCount,
  backupState,
  byteSize,
  drillState,
  durationParts,
  groupAlerts,
  laneTone,
  largestTables,
  sortWorkers,
  tableName,
  type AdminSystem,
  type AlertState,
  type MaintenanceRun,
  type WorkerPulse,
} from "./system";

const SECOND = 1_000_000;
const DAY = 24 * 60 * 60 * SECOND;
const NOW = 1_790_000_000 * SECOND;

function alert(overrides: Partial<AlertState>): AlertState {
  return {
    code: "dead_jobs",
    status: "firing",
    severity: "sev2",
    summary: "Queued jobs ran out of attempts.",
    figure: 3,
    threshold: 0,
    unit: "count",
    detail: "3 dead jobs: send_outbound_message 3",
    fired_at: NOW - 600 * SECOND,
    notification_count: 1,
    notified_at: NOW - 600 * SECOND,
    resolved_at: null,
    runbook: "docs/operations/runbooks/stuck-worker.md",
    ...overrides,
  };
}

function run(overrides: Partial<MaintenanceRun> = {}): MaintenanceRun {
  return {
    kind: "backup",
    outcome: "succeeded",
    started_at: NOW - DAY,
    finished_at: NOW - DAY + 60 * SECOND,
    archive_size: 1024,
    row_count: 10,
    release: "4718714c0f2e",
    error: null,
    ...overrides,
  };
}

function worker(overrides: Partial<WorkerPulse>): WorkerPulse {
  return {
    worker_id: "worker_1",
    host_name: "srv-a",
    started_at: NOW - DAY,
    beat_at: NOW,
    age_seconds: 4,
    is_stale: false,
    failing_jobs: [],
    release: "4718714c0f2e",
    ...overrides,
  };
}

function system(overrides: Partial<AdminSystem> = {}): AdminSystem {
  return {
    checked_at: NOW,
    workers: [],
    lanes: [],
    dead_jobs: [],
    channels_in_error: [],
    channels_in_error_count: 0,
    expiring_credentials: [],
    tables: [],
    is_backup_overdue: false,
    alerts: [],
    database_bytes: null,
    last_backup: null,
    last_restore_drill: null,
    ...overrides,
  };
}

describe("groupAlerts", () => {
  it("puts the most severe firing alert first, then the longest firing", () => {
    const groups = groupAlerts([
      alert({ code: "tool_errors", severity: "sev3", fired_at: NOW - 9_000 * SECOND }),
      alert({ code: "dead_jobs", severity: "sev2", fired_at: NOW - 60 * SECOND }),
      alert({ code: "inbound_backlog", severity: "sev2", fired_at: NOW - 900 * SECOND }),
      alert({ code: "llm_errors", severity: "sev1", fired_at: NOW - 30 * SECOND }),
      alert({ code: "otp_cap_trips", status: "resolved", resolved_at: NOW - 3_600 * SECOND }),
      alert({ code: "stale_worker", status: "resolved", resolved_at: NOW - 60 * SECOND }),
    ]);

    expect(groups.firing.map((item) => item.code)).toEqual(["llm_errors", "inbound_backlog", "dead_jobs", "tool_errors"]);
    expect(groups.resolved.map((item) => item.code)).toEqual(["stale_worker", "otp_cap_trips"]);
  });
});

describe("durationParts", () => {
  it("uses the largest unit that still reads exactly enough", () => {
    expect(durationParts(-3)).toEqual({ unit: "seconds", count: 0 });
    expect(durationParts(119.9)).toEqual({ unit: "seconds", count: 119 });
    expect(durationParts(120)).toEqual({ unit: "minutes", count: 2 });
    expect(durationParts(7_199)).toEqual({ unit: "minutes", count: 119 });
    expect(durationParts(7_200)).toEqual({ unit: "hours", count: 2 });
    expect(durationParts(48 * 3_600)).toEqual({ unit: "days", count: 2 });
  });
});

describe("byteSize", () => {
  it("counts in binary multiples with one decimal under ten", () => {
    expect(byteSize(812)).toEqual({ unit: "b", value: 812 });
    expect(byteSize(1024)).toEqual({ unit: "kb", value: 1 });
    expect(byteSize(4.24 * 1024 ** 3)).toEqual({ unit: "gb", value: 4.2 });
    expect(byteSize(37.4 * 1024 ** 2)).toEqual({ unit: "mb", value: 37 });
    expect(byteSize(-1)).toEqual({ unit: "b", value: 0 });
    expect(byteSize(3 * 1024 ** 5)).toEqual({ unit: "tb", value: 3072 });
  });

  it("carries a value that rounds up to the next unit", () => {
    expect(byteSize(1024 * 1024 - 100)).toEqual({ unit: "mb", value: 1 });
  });
});

describe("tables", () => {
  it("shows the largest first and drops the schema", () => {
    const tables = [
      { table: "workshop.bookings", total_bytes: 10, row_estimate: 1 },
      { table: "workshop.messages", total_bytes: 900, row_estimate: 50 },
      { table: "workshop.audit_log", total_bytes: 10, row_estimate: 2 },
    ];

    expect(largestTables(tables, 2).map((table) => table.table)).toEqual(["workshop.messages", "workshop.audit_log"]);
    expect(tableName("workshop.messages")).toBe("messages");
    expect(tableName("plain")).toBe("plain");
  });
});

describe("laneTone", () => {
  it("flags dead jobs before a backlog", () => {
    const lane = { lane: "inbound" as const, waiting: 1, scheduled: 0, running: 0, dead: 0, oldest_wait_seconds: 30 };

    expect(laneTone(lane)).toBeNull();
    expect(laneTone({ ...lane, oldest_wait_seconds: 121 })).toBe("warning");
    expect(laneTone({ ...lane, oldest_wait_seconds: 121, dead: 1 })).toBe("danger");
    expect(laneTone({ ...lane, oldest_wait_seconds: null })).toBeNull();
  });
});

describe("backups and drills", () => {
  it("reads the backup as missing, failed, overdue or fine", () => {
    expect(backupState(system())).toBe("missing");
    expect(backupState(system({ last_backup: run({ outcome: "failed", error: "pg_dump: error" }) }))).toBe("failed");
    expect(backupState(system({ last_backup: run(), is_backup_overdue: true }))).toBe("overdue");
    expect(backupState(system({ last_backup: run() }))).toBe("ok");
  });

  it("counts a drill late after eight days", () => {
    const drill = (finishedAt: number) => run({ kind: "restore_drill", finished_at: finishedAt });

    expect(drillState(system())).toBe("missing");
    expect(drillState(system({ last_restore_drill: run({ kind: "restore_drill", outcome: "failed" }) }))).toBe("failed");
    expect(drillState(system({ last_restore_drill: drill(NOW - 8 * DAY) }))).toBe("ok");
    expect(drillState(system({ last_restore_drill: drill(NOW - 8 * DAY - SECOND) }))).toBe("overdue");
  });
});

describe("workers and attention", () => {
  it("lists stale workers first", () => {
    const workers = sortWorkers([
      worker({ worker_id: "b", host_name: "srv-b" }),
      worker({ worker_id: "c", host_name: "srv-c", is_stale: true }),
      worker({ worker_id: "a", host_name: "srv-a" }),
    ]);

    expect(workers.map((item) => item.worker_id)).toEqual(["c", "a", "b"]);
  });

  it("adds up what wants a look now", () => {
    const busy = system({
      alerts: [alert({}), alert({ code: "llm_errors", status: "resolved", resolved_at: NOW })],
      workers: [worker({ is_stale: true }), worker({ worker_id: "worker_2" })],
      dead_jobs: [
        { name: "send_outbound_message", count: 2 },
        { name: "process_inbound_message", count: 1 },
      ],
      channels_in_error_count: 4,
    });

    expect(attentionCount(system())).toBe(0);
    expect(attentionCount(busy)).toBe(1 + 1 + 3 + 4);
  });
});

import { describe, expect, it } from "vitest";

import {
  archiveSize,
  canDownload,
  EXPORT_STATUS_TONES,
  hasWorkingExport,
  isExportWorking,
  isUsedUp,
  linkHref,
  MAX_EXPORT_DOWNLOADS,
  shownStatus,
  withDownloadCounted,
  withExport,
  type BusinessExport,
} from "./businessExports";

const HOUR_US = 3_600_000_000;
const NOW_US = 1_790_000_000_000_000;
const PATH = "/v1/business-exports/business_1/export_1/download?token=AAAAAAAAAAAAAAAAAAAAAAAAAAAA";

function exportOf(overrides: Partial<BusinessExport> = {}): BusinessExport {
  return {
    id: "export_1",
    status: "ready",
    requested_at: NOW_US - HOUR_US,
    finished_at: NOW_US - HOUR_US + 60_000_000,
    expires_at: NOW_US + 23 * HOUR_US,
    archive_bytes: 2_500_000,
    record_count: 1_234,
    downloads_left: MAX_EXPORT_DOWNLOADS,
    last_error: null,
    ...overrides,
  };
}

describe("isExportWorking / hasWorkingExport", () => {
  it("waits on queued and running exports only", () => {
    expect(isExportWorking(exportOf({ status: "queued" }))).toBe(true);
    expect(isExportWorking(exportOf({ status: "running" }))).toBe(true);
    for (const status of ["ready", "expired", "failed"] as const) {
      expect(isExportWorking(exportOf({ status }))).toBe(false);
    }
    expect(isExportWorking(null)).toBe(false);
    expect(hasWorkingExport(undefined)).toBe(false);
    expect(hasWorkingExport([exportOf(), exportOf({ id: "export_2", status: "running" })])).toBe(true);
    expect(hasWorkingExport([exportOf()])).toBe(false);
  });
});

describe("canDownload / isUsedUp", () => {
  it("downloads a ready export that is kept and has downloads left", () => {
    expect(canDownload(exportOf(), NOW_US)).toBe(true);
    expect(canDownload(exportOf({ expires_at: null, downloads_left: 1 }), NOW_US)).toBe(true);
    expect(isUsedUp(exportOf(), NOW_US)).toBe(false);
  });

  it("does not once it ran out, before it is ready, or after three downloads", () => {
    expect(canDownload(exportOf({ expires_at: NOW_US }), NOW_US)).toBe(false);
    expect(canDownload(exportOf({ status: "running" }), NOW_US)).toBe(false);
    expect(canDownload(exportOf({ status: "expired" }), NOW_US)).toBe(false);
    expect(canDownload(exportOf({ downloads_left: 0 }), NOW_US)).toBe(false);
    expect(isUsedUp(exportOf({ downloads_left: 0 }), NOW_US)).toBe(true);
    expect(isUsedUp(exportOf({ downloads_left: 0, expires_at: NOW_US }), NOW_US)).toBe(false);
  });
});

describe("linkHref", () => {
  it("goes through the cabinet's proxy, and only to the API", () => {
    expect(linkHref(PATH)).toBe(`/api/backend${PATH}`);
    expect(linkHref("https://example.com/v1/x")).toBeNull();
    expect(linkHref("//example.com/v1/x")).toBeNull();
  });
});

describe("withDownloadCounted", () => {
  it("counts one download of that export, never below zero", () => {
    const other = exportOf({ id: "export_2" });
    const counted = withDownloadCounted([exportOf(), other], "export_1");
    expect(counted.map((item) => item.downloads_left)).toEqual([2, 3]);
    expect(withDownloadCounted([exportOf({ downloads_left: 0 })], "export_1")[0]?.downloads_left).toBe(0);
    expect(withDownloadCounted(undefined, "export_1")).toEqual([]);
  });
});

describe("shownStatus", () => {
  it("reads a ready export past its day as expired", () => {
    expect(shownStatus(exportOf(), NOW_US)).toBe("ready");
    expect(shownStatus(exportOf({ expires_at: NOW_US - 1 }), NOW_US)).toBe("expired");
    expect(shownStatus(exportOf({ status: "failed", expires_at: null }), NOW_US)).toBe("failed");
    expect(shownStatus(exportOf({ expires_at: null }), NOW_US)).toBe("ready");
  });

  it("has a tone for every status", () => {
    expect(Object.keys(EXPORT_STATUS_TONES).sort()).toEqual(["expired", "failed", "queued", "ready", "running"]);
  });
});

describe("archiveSize", () => {
  it("counts kilobytes up to a megabyte, then megabytes to one decimal", () => {
    expect(archiveSize(10)).toEqual({ value: 1, unit: "kb" });
    expect(archiveSize(1_536)).toEqual({ value: 2, unit: "kb" });
    expect(archiveSize(1024 * 1024)).toEqual({ value: 1, unit: "mb" });
    expect(archiveSize(2_500_000)).toEqual({ value: 2.4, unit: "mb" });
  });
});

describe("withExport", () => {
  it("puts a new export first and replaces the one the API answered with again", () => {
    const older = exportOf({ id: "export_0", status: "expired" });
    const running = exportOf({ id: "export_2", status: "running", downloads_left: 0 });
    expect(withExport([older], running).map((item) => item.id)).toEqual(["export_2", "export_0"]);
    expect(withExport([running, older], { ...running, status: "queued" }).map((item) => item.status)).toEqual([
      "queued",
      "expired",
    ]);
    expect(withExport(undefined, running)).toEqual([running]);
  });
});

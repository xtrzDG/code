/**
 * The full exports of a business (POST and GET …/business-exports): what
 * each one's state means for Settings → Privacy. Pure functions, so the
 * card and the tests share them.
 */

import { BFF_BASE_PATH } from "@/api/client";
import type { Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui";

export type BusinessExport = Schema<"BusinessExportView">;
export type BusinessExportStatus = BusinessExport["status"];

/** While an export waits or is being built, look again this often. */
export const BUSINESS_EXPORT_POLL_MS = 4_000;

export const EXPORT_STATUS_TONES: Readonly<Record<BusinessExportStatus, BadgeTone>> = {
  queued: "info",
  running: "info",
  ready: "success",
  expired: "neutral",
  failed: "danger",
};

/** An export the worker has yet to finish: the card polls and the start button waits. */
export function isExportWorking(item: Pick<BusinessExport, "status"> | null | undefined): boolean {
  return item?.status === "queued" || item?.status === "running";
}

export function hasWorkingExport(items: readonly BusinessExport[] | undefined): boolean {
  return (items ?? []).some(isExportWorking);
}

/**
 * The browser's address of a ready export's signed link: the API's path
 * through the cabinet's proxy; null when there is nothing to download (not
 * ready, expired by now, or no link).
 */
export function downloadHref(item: BusinessExport, nowUs: number): string | null {
  if (item.status !== "ready" || !item.download_path || !item.download_path.startsWith("/v1/")) {
    return null;
  }
  if (item.expires_at !== null && item.expires_at !== undefined && item.expires_at <= nowUs) {
    return null;
  }
  return `${BFF_BASE_PATH}${item.download_path}`;
}

/** The status to show: a ready export whose link ran out reads as expired before the hourly sweep. */
export function shownStatus(item: BusinessExport, nowUs: number): BusinessExportStatus {
  if (item.status === "ready" && item.expires_at !== null && item.expires_at !== undefined && item.expires_at <= nowUs) {
    return "expired";
  }
  return item.status;
}

const KILOBYTE = 1024;
const MEGABYTE = 1024 * 1024;

/** An archive's size as the number and its unit ("kb" under a megabyte), one decimal at most. */
export function archiveSize(bytes: number): { value: number; unit: "kb" | "mb" } {
  if (bytes < MEGABYTE) {
    return { value: Math.max(1, Math.ceil(bytes / KILOBYTE)), unit: "kb" };
  }
  return { value: Math.round((bytes / MEGABYTE) * 10) / 10, unit: "mb" };
}

/** The list with a newly started export first (it replaces itself when the start returned the running one). */
export function withExport(items: readonly BusinessExport[] | undefined, started: BusinessExport): BusinessExport[] {
  return [started, ...(items ?? []).filter((item) => item.id !== started.id)];
}

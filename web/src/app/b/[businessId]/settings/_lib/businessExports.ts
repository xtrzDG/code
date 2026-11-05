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

/** The most times one export can be downloaded (the API's MAX_EXPORT_DOWNLOADS). */
export const MAX_EXPORT_DOWNLOADS = 3;

/** A ready export the owner can still download: kept, not run out, downloads left. */
export function canDownload(item: BusinessExport, nowUs: number): boolean {
  return shownStatus(item, nowUs) === "ready" && item.downloads_left > 0;
}

/** A ready export downloaded as many times as it may be: only a new export gives another copy. */
export function isUsedUp(item: BusinessExport, nowUs: number): boolean {
  return shownStatus(item, nowUs) === "ready" && item.downloads_left <= 0;
}

/**
 * The browser's address of a one-time link (POST …/download-link): the
 * API's path through the cabinet's proxy, which adds the owner's session;
 * null for a path outside the API.
 */
export function linkHref(downloadPath: string): string | null {
  return downloadPath.startsWith("/v1/") ? `${BFF_BASE_PATH}${downloadPath}` : null;
}

/** The list with one more download of an export counted (the API counts it as the link opens). */
export function withDownloadCounted(items: readonly BusinessExport[] | undefined, exportId: string): BusinessExport[] {
  return (items ?? []).map((item) =>
    item.id === exportId ? { ...item, downloads_left: Math.max(0, item.downloads_left - 1) } : item,
  );
}

/** The status to show: a ready export past its day reads as expired before the hourly sweep. */
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

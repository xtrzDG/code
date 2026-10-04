/**
 * The cabinet's tables as CSV files (GET …/exports/{table}): which tables
 * there are, the file name the API gave, and saving a downloaded file.
 * Pure functions apart from `saveFile`, so the tests share them.
 */

import { safeFileName } from "@/components/workspace/helpers";

export const CSV_TABLES = ["bookings", "leads", "contacts", "conversations", "audit_log"] as const;

export type CsvTable = (typeof CSV_TABLES)[number];

/** The query of a table's export: the list's own filters, strings only (unset ones left out). */
export type CsvQuery = Readonly<Record<string, string | undefined>>;

/**
 * The file name of a Content-Disposition header ("attachment;
 * filename="bookings-2026-10-04.csv"", or RFC 5987's filename*=UTF-8''…),
 * made safe for every system; `fallback` when the header names none.
 */
export function fileNameFromDisposition(header: string | null | undefined, fallback: string): string {
  if (!header) {
    return safeFileName(fallback);
  }
  const extended = /filename\*\s*=\s*(?:UTF-8|utf-8)''([^;]+)/.exec(header);
  if (extended?.[1]) {
    try {
      return safeFileName(decodeURIComponent(extended[1].trim()));
    } catch {
      // A broken escape: the plain name, if any, follows.
    }
  }
  const plain = /filename\s*=\s*(?:"([^"]*)"|([^;\s]+))/.exec(header);
  const name = plain?.[1] ?? plain?.[2];
  return safeFileName(name?.trim() ? name.trim() : fallback);
}

/** "bookings-2026-10-04.csv" when the API sent no name (it always does). */
export function fallbackCsvName(table: CsvTable, day: string): string {
  return `${table.replace(/_/g, "-")}-${day}.csv`;
}

/** The query without unset values, as openapi-fetch sends it. */
export function definedQuery(query: CsvQuery): Record<string, string> {
  return Object.fromEntries(
    Object.entries(query).filter((entry): entry is [string, string] => typeof entry[1] === "string" && entry[1] !== ""),
  );
}

/** Save a downloaded file in the browser. */
export function saveFile(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = safeFileName(fileName);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
}

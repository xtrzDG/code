/**
 * The Knowledge section's menu import: draft confidence, the uploaded file
 * and why a menu link could not be read.
 */

import { isApiError } from "@/api/errors";
import type { Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";
import { numberFormat } from "@/lib/intl/formatters";

export type ImportedMenuItem = Schema<"ImportedMenuItemView">;

export type ConfidenceLevel = "high" | "medium" | "low";

/** How sure the reader was about a line: ≥ 0.8 high, ≥ 0.5 medium, else low. */
export function confidenceLevel(confidence: number): ConfidenceLevel {
  if (confidence >= 0.8) {
    return "high";
  }
  return confidence >= 0.5 ? "medium" : "low";
}

/** Drafts checked at first: everything the reader was at least fairly sure of. */
export function initialImportSelection(items: readonly ImportedMenuItem[]): Set<string> {
  return new Set(items.filter((item) => confidenceLevel(item.confidence) !== "low").map((item) => item.item.id));
}

/** The largest file the API takes (15 MB, sent as base64). */
export const MENU_UPLOAD_MAX_BYTES = 15 * 1024 * 1024;

const MEDIA_TYPES_BY_EXTENSION: Record<string, string> = {
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
  webp: "image/webp",
  gif: "image/gif",
  pdf: "application/pdf",
  txt: "text/plain",
  csv: "text/csv",
  htm: "text/html",
  html: "text/html",
};

/** Media types the menu reader accepts for uploads. */
export const MENU_UPLOAD_MEDIA_TYPES: readonly string[] = [...new Set(Object.values(MEDIA_TYPES_BY_EXTENSION))];

/** `accept` of the file input. */
export const MENU_UPLOAD_ACCEPT = [...MENU_UPLOAD_MEDIA_TYPES, ...Object.keys(MEDIA_TYPES_BY_EXTENSION).map((ext) => `.${ext}`)].join(",");

/**
 * The media type to send for a chosen file: the browser's type when the
 * reader accepts it, else one from the extension (browsers often leave
 * .csv or .txt untyped). Null for unsupported files.
 */
export function menuMediaType(fileName: string, browserType: string): string | null {
  const type = browserType.trim().toLowerCase().split(";")[0] ?? "";
  if (type === "image/jpg" || type === "image/pjpeg") {
    return "image/jpeg";
  }
  if (MENU_UPLOAD_MEDIA_TYPES.includes(type)) {
    return type;
  }
  const extension = /\.([a-z0-9]+)$/i.exec(fileName.trim())?.[1]?.toLowerCase();
  return extension ? (MEDIA_TYPES_BY_EXTENSION[extension] ?? null) : null;
}

export type MenuFileCheck = { ok: true; mediaType: string } | { ok: false; error: MessageKey };

export function checkMenuFile(file: { name: string; type: string; size: number }): MenuFileCheck {
  const mediaType = menuMediaType(file.name, file.type);
  if (mediaType === null) {
    return { ok: false, error: "knowledge.import.errors.fileType" };
  }
  if (file.size === 0) {
    return { ok: false, error: "knowledge.import.errors.fileEmpty" };
  }
  if (file.size > MENU_UPLOAD_MAX_BYTES) {
    return { ok: false, error: "knowledge.import.errors.fileTooLarge" };
  }
  return { ok: true, mediaType };
}

/** "data:image/png;base64,AAAA" -> "AAAA". */
export function base64FromDataUrl(dataUrl: string): string {
  const comma = dataUrl.indexOf(",");
  return comma >= 0 ? dataUrl.slice(comma + 1) : dataUrl;
}

/** A file size for people: 1536 -> "1.5 KB" (decimal separator from the locale). */
export function formatFileSize(bytes: number, locale: string): string {
  const units = ["B", "KB", "MB"] as const;
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const number = numberFormat(locale, { maximumFractionDigits: unit === 0 ? 0 : 1 }).format(value);
  return `${number} ${units[unit]}`;
}

/** Why the API could not read a menu link (`reasons[].code` of its 422). */
export type MenuLinkProblemCode = "menu_link_invalid" | "menu_link_unreachable" | "menu_link_unreadable";

const MENU_LINK_PROBLEM_CODES: readonly MenuLinkProblemCode[] = ["menu_link_invalid", "menu_link_unreachable", "menu_link_unreadable"];

export interface MenuLinkProblem {
  code: MenuLinkProblemCode;
  /** The page's HTTP error status ("http_status:404"), when it answered with one. */
  status: number | null;
}

/** The link problem named by a failed import, or null for other errors (an unavailable reader, a bad file). */
export function menuLinkProblem(error: unknown): MenuLinkProblem | null {
  if (!isApiError(error) || error.status !== 422) {
    return null;
  }
  for (const reason of error.reasons) {
    const code = MENU_LINK_PROBLEM_CODES.find((known) => known === reason.code);
    if (code) {
      const status = reason.details
        .map((detail) => /^http_status:(\d{3})$/.exec(detail)?.[1])
        .find((value): value is string => value !== undefined);
      return { code, status: status ? Number(status) : null };
    }
  }
  return null;
}

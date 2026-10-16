/**
 * The import from the business's website: the address the owner typed,
 * how far an import got, and the words for why it could not read the site.
 */

import { isApiError } from "@/api/errors";
import type { Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

export type WebsiteImport = Schema<"WebsiteImportView">;
export type WebsiteImportStage = "queued" | "opening" | "reading" | "done" | "failed";

/**
 * What the owner typed as an absolute http(s) address ("cafe.ge" ->
 * "https://cafe.ge/"), or null when it is no web address at all. Whether
 * the site may be read is the API's decision.
 */
export function normalizeWebsiteAddress(input: string): string | null {
  const trimmed = input.trim();
  if (trimmed === "" || /\s/.test(trimmed)) {
    return null;
  }
  const withScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
  try {
    const url = new URL(withScheme);
    if ((url.protocol !== "http:" && url.protocol !== "https:") || !url.hostname.includes(".")) {
      return null;
    }
    return url.href;
  } catch {
    return null;
  }
}

/** The host of an address for people ("https://www.cafe.ge/ka/" -> "cafe.ge"). */
export function siteHost(address: string): string {
  try {
    return new URL(address).hostname.replace(/^www\./, "");
  } catch {
    return address;
  }
}

/** The path of a page for a short label ("https://cafe.ge/menu" -> "/menu"). */
export function pageLabel(address: string): string {
  try {
    const url = new URL(address);
    return `${url.pathname}${url.search}` || "/";
  } catch {
    return address;
  }
}

export function isImportRunning(view: WebsiteImport | null | undefined): boolean {
  return view?.status === "queued" || view?.status === "reading";
}

/** Where the import stands, for the progress text. */
export function importStage(view: WebsiteImport): WebsiteImportStage {
  if (view.status === "reading") {
    return view.pages_planned === 0 ? "opening" : "reading";
  }
  return view.status;
}

/** How far along the import is, 0 to 100 (never quite 100 before it is done). */
export function importPercent(view: WebsiteImport): number {
  switch (importStage(view)) {
    case "queued":
      return 4;
    case "opening":
      return 10;
    case "done":
    case "failed":
      return 100;
    case "reading": {
      const handled = view.pages_read + view.pages_skipped;
      return Math.min(96, Math.round(12 + (84 * handled) / Math.max(1, view.pages_planned)));
    }
  }
}

/** The page being read now (1-based), for "page 3 of 7". */
export function currentPage(view: WebsiteImport): number {
  return Math.min(view.pages_planned, view.pages_read + view.pages_skipped + 1);
}

export interface ProblemText {
  key: MessageKey;
  values?: Record<string, string | number>;
}

const DETAIL_TEXTS: Record<string, MessageKey> = {
  not_public: "knowledge.website.errors.notPublic",
  not_http: "knowledge.website.errors.notHttp",
  port_not_allowed: "knowledge.website.errors.port",
  credentials_in_url: "knowledge.website.errors.credentials",
  unknown_host: "knowledge.website.errors.unknownHost",
  timeout: "knowledge.website.errors.timeout",
};
const PROBLEM_TEXTS: Record<string, MessageKey> = {
  website_link_invalid: "knowledge.website.errors.notPublic",
  website_link_unreachable: "knowledge.website.errors.unreachable",
  website_link_unreadable: "knowledge.website.errors.unreadable",
  website_reader_unavailable: "knowledge.website.errors.reader",
  website_import_interrupted: "knowledge.website.errors.interrupted",
};

/** Why an import (or the start of one) could not read the site, in words. */
export function problemText(problem: string, detail: string | null | undefined): ProblemText {
  const status = /^http_status:(\d{3})$/.exec(detail ?? "")?.[1];
  if (status) {
    return { key: "knowledge.website.errors.httpStatus", values: { status: Number(status) } };
  }
  const detailCode = (detail ?? "").split(":")[0] ?? "";
  if (problem !== "website_link_unreadable" && DETAIL_TEXTS[detailCode]) {
    return { key: DETAIL_TEXTS[detailCode] };
  }
  return { key: PROBLEM_TEXTS[problem] ?? "knowledge.website.errors.unreachable" };
}

/** The words for a refused start, or null for errors the generic message covers. */
export function startProblemText(error: unknown): ProblemText | null {
  if (!isApiError(error)) {
    return null;
  }
  if (error.status === 409) {
    return { key: "knowledge.website.errors.running" };
  }
  if (error.status === 429) {
    return { key: "knowledge.website.errors.tooMany" };
  }
  const reason = error.reasons.find((candidate) => candidate.code.startsWith("website_"));
  if (error.status === 422) {
    return reason ? problemText(reason.code, reason.details[0]) : { key: "knowledge.website.errors.address" };
  }
  return null;
}

/** The website link of the business profile, offered as the address to read. */
export function profileWebsite(profile: Schema<"BusinessProfileView"> | undefined): string | null {
  return profile?.links?.find((link) => link.kind === "website")?.url ?? null;
}

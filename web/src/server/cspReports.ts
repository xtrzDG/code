/**
 * Content Security Policy violation reports, as browsers send them to
 * /api/csp-report: the old `report-uri` form (application/csp-report, one
 * {"csp-report": {...}}) and the Reporting API's (application/reports+json,
 * an array of {type: "csp-violation", body: {...}}). Each becomes a small
 * violation without personal data: the page's path (no query, no booking
 * key), the directive, what was blocked (a keyword such as "inline", or an
 * origin and path), where the code was. No sample, no referrer, no policy.
 */

import { withoutBookingToken } from "@/lib/bookingPage/paths";

/** A report is a few hundred bytes; a batch of the Reporting API a few kilobytes. */
export const MAX_CSP_REPORT_BYTES = 16 * 1024;
/** Violations kept from one request (the rest of a batch is dropped). */
const MAX_VIOLATIONS = 10;
const MAX_TEXT_LENGTH = 300;
const DIRECTIVE = /^[a-z][a-z-]{1,40}$/;
/** What a browser puts in place of a URL ("inline", "eval", "trusted-types-sink", ...). */
const KEYWORD = /^[a-z][a-z-]{1,40}$/;

const CSP_REPORT_CONTENT_TYPES = ["application/csp-report", "application/reports+json", "application/json"];

export interface CspViolation {
  /** The page's path, e.g. "/b/business_1/overview" ("/r/[token]" for a booking page). */
  documentPath: string;
  /** The directive that refused it: "style-src-attr", "require-trusted-types-for", ... */
  directive: string;
  /** "inline", "eval", "trusted-types-sink", ... or an address as origin and path. */
  blocked: string;
  /** The script that did it, as origin and path, when the browser knows. */
  sourceFile: string | null;
  line: number | null;
  column: number | null;
  /** "enforce" (refused) or "report" (a report-only policy). */
  disposition: "enforce" | "report";
}

type Raw = Record<string, unknown>;

function isRecord(value: unknown): value is Raw {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() !== "" ? value.trim() : null;
}

function position(value: unknown): number | null {
  return typeof value === "number" && Number.isInteger(value) && value >= 0 && value < 10_000_000 ? value : null;
}

/** An address as origin and path (no query, fragment or credentials); a keyword as it is. */
function address(value: unknown): string | null {
  const raw = text(value);
  if (raw === null) {
    return null;
  }
  if (KEYWORD.test(raw)) {
    return raw;
  }
  try {
    const url = new URL(raw);
    const kept = url.protocol === "http:" || url.protocol === "https:" ? `${url.origin}${url.pathname}` : url.protocol;
    return withoutBookingToken(kept).slice(0, MAX_TEXT_LENGTH);
  } catch {
    return null;
  }
}

function documentPath(value: unknown): string | null {
  const raw = text(value);
  if (raw === null) {
    return null;
  }
  try {
    return withoutBookingToken(new URL(raw).pathname).slice(0, MAX_TEXT_LENGTH);
  } catch {
    return null;
  }
}

function directiveOf(...candidates: unknown[]): string | null {
  for (const candidate of candidates) {
    // "style-src-elem 'self' 'nonce-…'" (an old violated-directive) names it first.
    const name = text(candidate)?.split(" ")[0] ?? null;
    if (name !== null && DIRECTIVE.test(name)) {
      return name;
    }
  }
  return null;
}

function violation(fields: {
  document: unknown;
  directive: unknown;
  violated?: unknown;
  blocked: unknown;
  source: unknown;
  line: unknown;
  column: unknown;
  disposition: unknown;
}): CspViolation | null {
  const path = documentPath(fields.document);
  const directive = directiveOf(fields.directive, fields.violated);
  if (path === null || directive === null) {
    return null;
  }
  return {
    documentPath: path,
    directive,
    blocked: address(fields.blocked) ?? "unknown",
    sourceFile: address(fields.source),
    line: position(fields.line),
    column: position(fields.column),
    disposition: fields.disposition === "report" ? "report" : "enforce",
  };
}

/** One `report-uri` report: {"csp-report": {...}}. */
function fromLegacyReport(body: Raw): CspViolation | null {
  const report = body["csp-report"];
  if (!isRecord(report)) {
    return null;
  }
  return violation({
    document: report["document-uri"],
    directive: report["effective-directive"],
    violated: report["violated-directive"],
    blocked: report["blocked-uri"],
    source: report["source-file"],
    line: report["line-number"],
    column: report["column-number"],
    disposition: report.disposition,
  });
}

/** One Reporting API report of the "csp-violation" type. */
function fromReportingApi(report: unknown): CspViolation | null {
  if (!isRecord(report) || report.type !== "csp-violation" || !isRecord(report.body)) {
    return null;
  }
  const body = report.body;
  return violation({
    document: body.documentURL ?? report.url,
    directive: body.effectiveDirective,
    blocked: body.blockedURL,
    source: body.sourceFile,
    line: body.lineNumber,
    column: body.columnNumber,
    disposition: body.disposition,
  });
}

/**
 * The violations of a report body; null when it is not one (not JSON, or
 * neither form). Unreadable entries of a batch are skipped.
 */
export function parseCspReports(body: string): CspViolation[] | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(body);
  } catch {
    return null;
  }
  if (Array.isArray(parsed)) {
    return parsed
      .slice(0, MAX_VIOLATIONS * 4)
      .map(fromReportingApi)
      .filter((item): item is CspViolation => item !== null)
      .slice(0, MAX_VIOLATIONS);
  }
  if (isRecord(parsed)) {
    const single = fromLegacyReport(parsed);
    return single === null ? null : [single];
  }
  return null;
}

export function isCspReportContentType(header: string | null): boolean {
  const type = (header ?? "").split(";")[0]?.trim().toLowerCase() ?? "";
  return CSP_REPORT_CONTENT_TYPES.includes(type);
}

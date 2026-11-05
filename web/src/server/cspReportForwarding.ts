/**
 * Where /api/csp-report sends what it accepts: Sentry's security endpoint
 * of the SENTRY_DSN project (Sentry groups the reports by directive and
 * blocked address), one cleaned report per violation. And how much it
 * accepts: a fixed window per client address (the one the cabinet's
 * proxies vouch for, TRUSTED_PROXY_HOPS) with a bounded number of
 * addresses, under a window for all of them.
 */

import { readDsn, readRelease } from "@/lib/monitoring/options";

import { trustedForwardedFor } from "./backend";
import type { CspViolation } from "./cspReports";

type Environment = Record<string, string | undefined>;

/** Sentry's CSP report endpoint of the configured project, or null without SENTRY_DSN. */
export function sentrySecurityUrl(env: Environment): string | null {
  const dsn = readDsn(env);
  if (dsn === null) {
    return null;
  }
  try {
    const parsed = new URL(dsn);
    const projectId = parsed.pathname.split("/").filter(Boolean).at(-1) ?? "";
    if (!/^https?:$/.test(parsed.protocol) || !parsed.username || !/^\d+$/.test(projectId)) {
      return null;
    }
    const target = new URL(`${parsed.origin}/api/${projectId}/security/`);
    target.searchParams.set("sentry_key", parsed.username);
    target.searchParams.set("sentry_environment", env.NODE_ENV ?? "production");
    const release = readRelease(env);
    if (release) {
      target.searchParams.set("sentry_release", release);
    }
    return target.toString();
  } catch {
    return null;
  }
}

/** The violation as a `report-uri` report, the form Sentry's endpoint reads. */
export function sentryCspReport(violation: CspViolation, siteOrigin: string): string {
  return JSON.stringify({
    "csp-report": {
      "document-uri": `${siteOrigin}${violation.documentPath}`,
      "effective-directive": violation.directive,
      "violated-directive": violation.directive,
      "blocked-uri": violation.blocked,
      ...(violation.sourceFile === null ? {} : { "source-file": violation.sourceFile }),
      ...(violation.line === null ? {} : { "line-number": violation.line }),
      ...(violation.column === null ? {} : { "column-number": violation.column }),
      disposition: violation.disposition,
    },
  });
}

/** The client a report is counted against: its address as the cabinet's proxies saw it, else one shared key. */
export function reportClientKey(headers: Headers, env: Environment = process.env): string {
  return trustedForwardedFor(headers, env)?.split(",")[0]?.trim() || "direct";
}

/**
 * A fixed window per key (at most `limit` per `windowMs`), keeping at
 * most `maxKeys` windows: expired ones go first, then the oldest.
 */
export function createKeyedWindowLimiter(
  limit: number,
  windowMs: number,
  maxKeys: number,
  now: () => number = Date.now,
): (key: string) => boolean {
  const windows = new Map<string, { start: number; count: number }>();

  function makeRoom(current: number): void {
    for (const [key, window] of windows) {
      if (current - window.start >= windowMs) {
        windows.delete(key);
      }
    }
    while (windows.size >= maxKeys) {
      const oldest = windows.keys().next();
      if (oldest.done) {
        return;
      }
      windows.delete(oldest.value);
    }
  }

  return function tryAcquire(key: string): boolean {
    const current = now();
    let window = windows.get(key);
    if (window === undefined || current - window.start >= windowMs) {
      windows.delete(key);
      if (windows.size >= maxKeys) {
        makeRoom(current);
      }
      window = { start: current, count: 0 };
      windows.set(key, window);
    }
    if (window.count >= limit) {
      return false;
    }
    window.count += 1;
    return true;
  };
}

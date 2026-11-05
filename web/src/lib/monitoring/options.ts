/**
 * Sentry settings of the cabinet, from its environment: SENTRY_DSN (none:
 * nothing is sent), SENTRY_TRACES_SAMPLE_RATE (share of traced server
 * requests, default 0.05) and the release (APP_RELEASE, on Render the
 * commit it built, RENDER_GIT_COMMIT).
 */

import { scrubEvent } from "./scrub";

type Environment = Record<string, string | undefined>;

/** Browser errors go to the cabinet's own origin, which forwards them (CSP, ad blockers). */
export const TUNNEL_PATH = "/api/monitoring";
/**
 * The browser never learns the project's DSN: it addresses this placeholder,
 * and the tunnel puts the configured DSN in its place.
 */
export const TUNNEL_PLACEHOLDER_DSN = "https://public@monitoring.invalid/1";
export const DEFAULT_TRACES_SAMPLE_RATE = 0.05;

export interface ServerMonitoringOptions {
  dsn: string;
  environment: string;
  release?: string;
  tracesSampleRate: number;
  sendDefaultPii: false;
  beforeSend: typeof scrubEvent;
  beforeSendTransaction: typeof scrubEvent;
}

export function readSampleRate(raw: string | undefined): number {
  const rate = raw === undefined || raw.trim() === "" ? DEFAULT_TRACES_SAMPLE_RATE : Number(raw);
  return Number.isFinite(rate) && rate >= 0 && rate <= 1 ? rate : DEFAULT_TRACES_SAMPLE_RATE;
}

export function readRelease(env: Environment): string | undefined {
  return env.APP_RELEASE?.trim() || env.RENDER_GIT_COMMIT?.trim() || undefined;
}

/** The DSN the cabinet reports to, or null when SENTRY_DSN is not set. */
export function readDsn(env: Environment): string | null {
  return env.SENTRY_DSN?.trim() || null;
}

/** Options of the server SDK, or null when Sentry is not configured. */
export function serverOptions(env: Environment): ServerMonitoringOptions | null {
  const dsn = readDsn(env);
  if (dsn === null) {
    return null;
  }
  return {
    dsn,
    environment: env.NODE_ENV ?? "production",
    release: readRelease(env),
    tracesSampleRate: readSampleRate(env.SENTRY_TRACES_SAMPLE_RATE),
    sendDefaultPii: false,
    beforeSend: scrubEvent,
    beforeSendTransaction: scrubEvent,
  };
}

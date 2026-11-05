/**
 * Browser errors of the cabinet to Sentry, through the tunnel. The Sentry
 * browser SDK is downloaded only when the first error happens, so pages
 * never pay for it; at most a few distinct errors per page are sent.
 */

import { TUNNEL_PATH, TUNNEL_PLACEHOLDER_DSN } from "./options";
import { scrubEvent } from "./scrub";

export const MAX_CLIENT_REPORTS = 5;

/** The part of @sentry/nextjs (browser) the reporter uses. */
export interface BrowserSentry {
  init(options: Record<string, unknown>): unknown;
  captureException(error: unknown): unknown;
  dedupeIntegration(): unknown;
  linkedErrorsIntegration(): unknown;
}

function browserOptions(sentry: BrowserSentry, environment: string): Record<string, unknown> {
  return {
    dsn: TUNNEL_PLACEHOLDER_DSN,
    tunnel: TUNNEL_PATH,
    environment,
    sendDefaultPii: false,
    // Only what is reported here: no global handlers (they would report
    // twice), no breadcrumbs of what owners click and type.
    defaultIntegrations: false,
    integrations: [sentry.dedupeIntegration(), sentry.linkedErrorsIntegration()],
    beforeSend: scrubEvent,
  };
}

function errorKey(error: unknown): string {
  if (error instanceof Error) {
    return `${error.name}:${error.message}`;
  }
  return String(error);
}

export function createClientReporter(load: () => Promise<BrowserSentry>, environment: string) {
  let sentry: Promise<BrowserSentry | null> | null = null;
  const reported = new Set<string>();

  function loadOnce(): Promise<BrowserSentry | null> {
    sentry ??= load().then(
      (sdk) => {
        sdk.init(browserOptions(sdk, environment));
        return sdk;
      },
      () => null,
    );
    return sentry;
  }

  return async function report(error: unknown): Promise<boolean> {
    const key = errorKey(error);
    if (reported.size >= MAX_CLIENT_REPORTS || reported.has(key)) {
      return false;
    }
    reported.add(key);
    const sdk = await loadOnce();
    if (sdk === null) {
      return false;
    }
    sdk.captureException(error);
    return true;
  };
}

export const reportClientError = createClientReporter(
  () => import("@sentry/nextjs") as Promise<BrowserSentry>,
  process.env.NODE_ENV ?? "production",
);

/**
 * Source maps of the cabinet for Sentry, read at build time by
 * next.config.ts. Only a build that has SENTRY_AUTH_TOKEN (CI on main,
 * .github/workflows/ci.yml) uploads them, to SENTRY_ORG / SENTRY_PROJECT,
 * for the release the cabinet reports (APP_RELEASE: the commit, see
 * ./options), and deletes them afterwards so the cabinet never serves
 * them. Every other build stays exactly as it was: no Sentry build plugin,
 * no instrumentation added to the server, no route list in the bundle.
 */

import type { SentryBuildOptions } from "@sentry/nextjs/config";

import { readRelease } from "./options";

type Environment = Record<string, string | undefined>;

export function warnUploadFailed(error: Error): void {
  console.warn(`Sentry source map upload failed: ${error.message}`);
}

/** Options of `withSentryConfig`, or null when this build uploads nothing. */
export function sourceMapUploadOptions(env: Environment): SentryBuildOptions | null {
  const authToken = env.SENTRY_AUTH_TOKEN?.trim();
  if (!authToken) {
    return null;
  }
  const release = readRelease(env);
  return {
    authToken,
    org: env.SENTRY_ORG?.trim() || undefined,
    project: env.SENTRY_PROJECT?.trim() || undefined,
    // Without a release name the maps are still found by the debug ids
    // the build writes into each file.
    release: release === undefined ? { create: false } : { name: release, create: true, finalize: true },
    sourcemaps: { deleteSourcemapsAfterUpload: true },
    telemetry: false,
    silent: false,
    // A failed upload (Sentry unreachable) costs readable stack traces of
    // this release, not the build.
    errorHandler: warnUploadFailed,
    // Only the upload: the server keeps the instrumentation it already has
    // (src/instrumentation.ts) and the browser bundle no list of routes.
    buildTimeInstrumentation: false,
    routeManifestInjection: false,
    // The cabinet reports errors only, not navigations.
    suppressOnRouterTransitionStartWarning: true,
    webpack: {
      autoInstrumentServerFunctions: false,
      autoInstrumentMiddleware: false,
      autoInstrumentAppDirectory: false,
    },
  };
}

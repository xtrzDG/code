/**
 * Server-side error reporting of the cabinet (Next.js instrumentation):
 * with SENTRY_DSN set, Sentry starts with the server and every error of a
 * page, route handler or Server Action is reported without personal data
 * (src/lib/monitoring). Without it nothing is loaded.
 */

import type { Instrumentation } from "next";

import { serverOptions } from "@/lib/monitoring/options";

let captureRequestError: Instrumentation.onRequestError | null = null;

export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME !== "nodejs") {
    return;
  }
  const options = serverOptions(process.env);
  if (options === null) {
    return;
  }
  const Sentry = await import("@sentry/nextjs");
  Sentry.init(options);
  captureRequestError = Sentry.captureRequestError;
}

export const onRequestError: Instrumentation.onRequestError = async (error, request, context) => {
  if (captureRequestError !== null) {
    await captureRequestError(error, request, context);
  }
};

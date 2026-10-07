/**
 * The cabinet's own telemetry: Web Vitals of its pages and the steps of
 * the setup tunnel, sent in batches to POST /v1/telemetry/events (through
 * the BFF, with the session). Best effort by design: a report never delays
 * or breaks a page; a batch the API refuses (429 after 30 batches a
 * minute, 401 without a session) is dropped, and after a 429 nothing is
 * sent until its Retry-After has passed.
 *
 * Reports wait a few seconds so they travel together; a page that is
 * hidden or left sends what it has at once (`keepalive`, so the request
 * outlives the page).
 */

import { api } from "@/api/client";
import type { RequestBody } from "@/api/types";

export type TelemetryReport = RequestBody<"/v1/telemetry/events", "post">["events"][number];
export type WebVitalReport = Extract<TelemetryReport, { kind: "web_vital" }>;
export type TunnelStepReport = Extract<TelemetryReport, { kind: "tunnel_step" }>;

/** The API takes at most 50 reports in one batch. */
export const MAX_BATCH = 50;
/** Reports kept while waiting; more are dropped (a page in a loop). */
export const MAX_QUEUE = 200;
export const FLUSH_DELAY_MS = 5_000;

interface SendResult {
  status: number;
  retryAfterSeconds?: number;
}

export interface TelemetryQueueOptions {
  send: (reports: TelemetryReport[], keepalive: boolean) => Promise<SendResult>;
  now?: () => number;
  schedule?: (flush: () => void, delayMs: number) => unknown;
  cancel?: (handle: unknown) => void;
}

export interface TelemetryQueue {
  track(report: TelemetryReport): void;
  /** Send what waits now; `keepalive` when the page is going away. */
  flush(keepalive?: boolean): Promise<void>;
  size(): number;
}

export function createTelemetryQueue(options: TelemetryQueueOptions): TelemetryQueue {
  const now = options.now ?? (() => Date.now());
  const schedule = options.schedule ?? ((flush, delay) => setTimeout(flush, delay));
  const cancel = options.cancel ?? ((handle) => clearTimeout(handle as ReturnType<typeof setTimeout>));
  let queue: TelemetryReport[] = [];
  let timer: unknown = null;
  let quietUntil = 0;

  async function flush(keepalive = false): Promise<void> {
    if (timer !== null) {
      cancel(timer);
      timer = null;
    }
    while (queue.length > 0) {
      if (now() < quietUntil) {
        queue = [];
        return;
      }
      const batch = queue.slice(0, MAX_BATCH);
      queue = queue.slice(MAX_BATCH);
      let result: SendResult;
      try {
        result = await options.send(batch, keepalive);
      } catch {
        return;
      }
      if (result.status === 429) {
        quietUntil = now() + Math.max(1, result.retryAfterSeconds ?? 60) * 1000;
        queue = [];
        return;
      }
    }
  }

  return {
    track(report) {
      if (now() < quietUntil || queue.length >= MAX_QUEUE) {
        return;
      }
      queue.push(report);
      if (queue.length >= MAX_BATCH) {
        void flush();
      } else if (timer === null) {
        timer = schedule(() => {
          timer = null;
          void flush();
        }, FLUSH_DELAY_MS);
      }
    },
    flush,
    size: () => queue.length,
  };
}

async function sendThroughBff(reports: TelemetryReport[], keepalive: boolean): Promise<SendResult> {
  const { response } = await api.POST("/v1/telemetry/events", { body: { events: reports }, keepalive });
  const retryAfter = Number(response.headers.get("retry-after"));
  return { status: response.status, retryAfterSeconds: Number.isFinite(retryAfter) ? retryAfter : undefined };
}

let shared: TelemetryQueue | null = null;

function sharedQueue(): TelemetryQueue {
  if (shared === null) {
    const queue = createTelemetryQueue({ send: sendThroughBff });
    const leave = () => void queue.flush(true);
    window.addEventListener("pagehide", leave);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") {
        leave();
      }
    });
    shared = queue;
  }
  return shared;
}

/** Queue one report (in the browser; elsewhere nothing happens). */
export function track(report: TelemetryReport): void {
  if (typeof window === "undefined") {
    return;
  }
  sharedQueue().track(report);
}

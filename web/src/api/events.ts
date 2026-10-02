/**
 * The live event stream of a business, read with fetch through the BFF
 * (GET /api/backend/v1/businesses/{id}/events, Server-Sent Events).
 *
 *     const stream = new LiveEventStream({ businessId, onEvent, onResync, onStatus });
 *     stream.start();   // connects, and keeps reconnecting
 *     stream.stop();
 *
 * It reconnects with growing pauses (1 s, 2 s, 4 s … 30 s, with jitter;
 * never sooner than the API's Retry-After), at once after the server ended
 * a stream normally (every 15 minutes), and when the connection went quiet
 * for longer than 2.5 heartbeats (a laptop waking up, a dropped network).
 * Each reconnect sends the last event id, so the API replays what was
 * missed or asks for a resync. A refused stream (signed out, no access)
 * stops for good. The live provider maps events to `invalidate(prefix)`.
 */

import { api } from "./client";
import { EventStreamParser } from "./eventStreamParser";
import { readLiveEvent, readStreamTimings, STREAM_READY, STREAM_RESYNC, type LiveEvent } from "./liveEvents";

export type LiveStreamStatus = "connecting" | "live" | "reconnecting" | "stopped";

/** Opens one stream; resolves with the API's answer (its body is the stream). */
export type OpenEventStream = (lastEventId: string | null, signal: AbortSignal) => Promise<Response>;

export interface LiveEventStreamOptions {
  businessId: string;
  onEvent: (event: LiveEvent) => void;
  /** Events may have been missed: reload what is shown. */
  onResync: () => void;
  onStatus: (status: LiveStreamStatus) => void;
  open?: OpenEventStream;
  random?: () => number;
}

const FIRST_DELAY_MS = 1_000;
const MAX_DELAY_MS = 30_000;
/** After a normal end the next stream opens almost at once (spread a little). */
const RENEW_DELAY_MS = 250;
const DEFAULT_HEARTBEAT_SECONDS = 20;
const QUIET_HEARTBEATS = 2.5;
/** Answers that will not change by trying again. */
const FINAL_STATUSES: ReadonlySet<number> = new Set([401, 403, 404]);

/** The pause before reconnect attempt `attempt` (0-based), in milliseconds. */
export function reconnectDelayMs(attempt: number, random: () => number = Math.random, retryAfterMs = 0): number {
  const base = Math.min(MAX_DELAY_MS, FIRST_DELAY_MS * 2 ** Math.max(0, attempt));
  const jittered = Math.round(base * (0.8 + 0.4 * random()));
  return Math.max(jittered, retryAfterMs);
}

/** Retry-After in milliseconds (seconds or an HTTP date), 0 when absent. */
export function retryAfterMs(value: string | null, now: number = Date.now()): number {
  if (!value) {
    return 0;
  }
  const seconds = Number(value);
  if (Number.isFinite(seconds)) {
    return Math.max(0, seconds * 1000);
  }
  const date = Date.parse(value);
  return Number.isNaN(date) ? 0 : Math.max(0, date - now);
}

function openThroughApi(businessId: string): OpenEventStream {
  return async (lastEventId, signal) => {
    const { response } = await api.GET("/v1/businesses/{business_id}/events", {
      params: { path: { business_id: businessId }, header: lastEventId ? { "Last-Event-ID": lastEventId } : undefined },
      headers: { Accept: "text/event-stream" },
      parseAs: "stream",
      signal,
    });
    return response;
  };
}

export class LiveEventStream {
  private readonly options: LiveEventStreamOptions;
  private readonly open: OpenEventStream;
  private readonly random: () => number;
  private readonly parser = new EventStreamParser();
  private abort: AbortController | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private watchdog: ReturnType<typeof setTimeout> | null = null;
  private attempt = 0;
  private quietMs = DEFAULT_HEARTBEAT_SECONDS * QUIET_HEARTBEATS * 1000;
  private hasBeenLive = false;
  private isStopped = true;

  constructor(options: LiveEventStreamOptions) {
    this.options = options;
    this.open = options.open ?? openThroughApi(options.businessId);
    this.random = options.random ?? Math.random;
  }

  start(): void {
    if (!this.isStopped) {
      return;
    }
    this.isStopped = false;
    void this.connect();
  }

  stop(): void {
    this.isStopped = true;
    this.clearTimers();
    this.abort?.abort();
    this.abort = null;
    this.options.onStatus("stopped");
  }

  /** Try again now (back online, the person asked): skips the pause. */
  reconnectNow(): void {
    if (this.isStopped) {
      this.start();
      return;
    }
    this.attempt = 0;
    this.clearTimers();
    this.abort?.abort();
    void this.connect();
  }

  private async connect(): Promise<void> {
    const abort = new AbortController();
    this.abort = abort;
    this.options.onStatus(this.hasBeenLive ? "reconnecting" : "connecting");
    let response: Response;
    try {
      response = await this.open(this.parser.lastEventId, abort.signal);
    } catch {
      this.retry(abort);
      return;
    }
    if (FINAL_STATUSES.has(response.status)) {
      this.stop();
      return;
    }
    if (!response.ok || !response.body) {
      this.retry(abort, retryAfterMs(response.headers.get("retry-after")));
      return;
    }
    await this.read(response.body, abort);
  }

  private async read(body: ReadableStream<Uint8Array>, abort: AbortController): Promise<void> {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    const onAbort = () => void reader.cancel().catch(() => undefined);
    abort.signal.addEventListener("abort", onAbort, { once: true });
    this.armWatchdog(abort);
    try {
      for (;;) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }
        for (const message of this.parser.push(decoder.decode(value, { stream: true }))) {
          this.handle(message.event, message);
        }
        // Any bytes (a heartbeat too) prove the connection alive.
        this.armWatchdog(abort);
      }
    } catch {
      // The connection broke or was aborted: reconnect below.
    } finally {
      abort.signal.removeEventListener("abort", onAbort);
    }
    if (this.abort !== abort || this.isStopped) {
      return;
    }
    const endedNormally = !abort.signal.aborted && this.attempt === 0 && this.hasBeenLive;
    this.retry(abort, 0, endedNormally);
  }

  private handle(name: string, message: Parameters<typeof readLiveEvent>[0]): void {
    if (name === STREAM_READY) {
      this.attempt = 0;
      this.hasBeenLive = true;
      this.quietMs = readStreamTimings(message).heartbeatSeconds * QUIET_HEARTBEATS * 1000;
      this.options.onStatus("live");
      return;
    }
    if (name === STREAM_RESYNC) {
      this.options.onResync();
      return;
    }
    const event = readLiveEvent(message);
    if (event) {
      this.options.onEvent(event);
    }
  }

  private armWatchdog(abort: AbortController): void {
    if (this.watchdog !== null) {
      clearTimeout(this.watchdog);
    }
    this.watchdog = setTimeout(() => abort.abort(), this.quietMs);
  }

  private retry(abort: AbortController, minimumMs = 0, isRenewal = false): void {
    if (this.isStopped || this.abort !== abort) {
      return;
    }
    this.clearTimers();
    const delay = isRenewal
      ? Math.round(RENEW_DELAY_MS * this.random())
      : reconnectDelayMs(this.attempt++, this.random, minimumMs);
    this.options.onStatus(this.hasBeenLive ? "reconnecting" : "connecting");
    this.timer = setTimeout(() => {
      this.timer = null;
      void this.connect();
    }, delay);
  }

  private clearTimers(): void {
    if (this.timer !== null) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    if (this.watchdog !== null) {
      clearTimeout(this.watchdog);
      this.watchdog = null;
    }
  }
}

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LiveEventStream, reconnectDelayMs, retryAfterMs, type LiveStreamStatus, type OpenEventStream } from "./events";
import type { LiveEvent } from "./liveEvents";

const READY = 'event: stream.ready\ndata: {"heartbeat_seconds":1,"lifetime_seconds":60}\n\n';

/** A response whose body the test writes to. */
function controlledResponse(init: ResponseInit = {}) {
  let controller!: ReadableStreamDefaultController<Uint8Array>;
  const body = new ReadableStream<Uint8Array>({ start: (c) => (controller = c) });
  const encoder = new TextEncoder();
  return {
    response: new Response(body, { headers: { "content-type": "text/event-stream" }, ...init }),
    write: (text: string) => controller.enqueue(encoder.encode(text)),
    end: () => controller.close(),
  };
}

function harness(open: OpenEventStream) {
  const events: LiveEvent[] = [];
  const statuses: LiveStreamStatus[] = [];
  let resyncs = 0;
  const stream = new LiveEventStream({
    businessId: "business_1",
    open,
    random: () => 0.5,
    onEvent: (event) => events.push(event),
    onResync: () => (resyncs += 1),
    onStatus: (status) => statuses.push(status),
  });
  return { stream, events, statuses, resyncs: () => resyncs };
}

async function flush(): Promise<void> {
  for (let index = 0; index < 10; index += 1) {
    await Promise.resolve();
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("reconnect pauses", () => {
  it("grow from one second to half a minute, with jitter", () => {
    expect(reconnectDelayMs(0, () => 0.5)).toBe(1_000);
    expect(reconnectDelayMs(3, () => 0.5)).toBe(8_000);
    expect(reconnectDelayMs(10, () => 0.5)).toBe(30_000);
    expect(reconnectDelayMs(0, () => 0)).toBe(800);
    expect(reconnectDelayMs(0, () => 1)).toBe(1_200);
  });

  it("never come sooner than the API's Retry-After", () => {
    expect(reconnectDelayMs(0, () => 0.5, 30_000)).toBe(30_000);
    expect(retryAfterMs("30")).toBe(30_000);
    expect(retryAfterMs(null)).toBe(0);
    expect(retryAfterMs("Thu, 01 Jan 1970 00:00:10 GMT", 4_000)).toBe(6_000);
    expect(retryAfterMs("someday")).toBe(0);
  });
});

describe("the live event stream", () => {
  it("goes live, hands over events and resyncs, and resumes from the last id", async () => {
    const first = controlledResponse();
    const second = controlledResponse();
    const open = vi.fn<OpenEventStream>().mockResolvedValueOnce(first.response).mockResolvedValueOnce(second.response);
    const { stream, events, statuses, resyncs } = harness(open);

    stream.start();
    await flush();
    first.write(READY);
    first.write('id: 017-a\nevent: handoff.created\ndata: {"ids":["handoff_1"],"occurred_at":5}\n\n');
    first.write("event: stream.resync\ndata: {}\n\n: heartbeat\n\n");
    await flush();
    first.end();
    await flush();
    await vi.advanceTimersByTimeAsync(300);

    expect(statuses.slice(0, 2)).toEqual(["connecting", "live"]);
    expect(events).toEqual([{ id: "017-a", event: "handoff.created", ids: ["handoff_1"], occurredAt: 5 }]);
    expect(resyncs()).toBe(1);
    expect(open).toHaveBeenCalledTimes(2);
    expect(open.mock.calls[1]![0]).toBe("017-a");
    expect(statuses).toContain("reconnecting");
    stream.stop();
  });

  it("backs off after failures and honours Retry-After", async () => {
    const live = controlledResponse();
    const open = vi
      .fn<OpenEventStream>()
      .mockRejectedValueOnce(new TypeError("offline"))
      .mockResolvedValueOnce(new Response("{}", { status: 429, headers: { "retry-after": "5" } }))
      .mockResolvedValueOnce(live.response);
    const { stream, statuses } = harness(open);

    stream.start();
    await flush();
    expect(open).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1_000);
    await flush();
    expect(open).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(4_000);
    expect(open).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(1_100);
    await flush();
    expect(open).toHaveBeenCalledTimes(3);
    expect(statuses.every((status) => status === "connecting")).toBe(true);
    stream.stop();
  });

  it("stops for good when the person may not listen", async () => {
    const open = vi.fn<OpenEventStream>().mockResolvedValue(new Response("{}", { status: 404 }));
    const { stream, statuses } = harness(open);

    stream.start();
    await flush();
    await vi.advanceTimersByTimeAsync(60_000);

    expect(open).toHaveBeenCalledTimes(1);
    expect(statuses.at(-1)).toBe("stopped");
  });

  it("reconnects when the connection goes quiet, and at once when asked", async () => {
    const quiet = controlledResponse();
    const next = controlledResponse();
    const third = controlledResponse();
    const open = vi
      .fn<OpenEventStream>()
      .mockResolvedValueOnce(quiet.response)
      .mockResolvedValueOnce(next.response)
      .mockResolvedValueOnce(third.response);
    const { stream } = harness(open);

    stream.start();
    await flush();
    quiet.write(READY);
    await flush();
    await vi.advanceTimersByTimeAsync(2_600);
    await flush();
    await vi.advanceTimersByTimeAsync(1_300);
    await flush();
    expect(open).toHaveBeenCalledTimes(2);

    stream.reconnectNow();
    await flush();
    expect(open).toHaveBeenCalledTimes(3);
    stream.stop();
    stream.reconnectNow();
    await flush();
    expect(open).toHaveBeenCalledTimes(4);
    stream.stop();
  });
});

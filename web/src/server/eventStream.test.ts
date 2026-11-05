import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { eventStreamHeaders, isEventStreamPath, relayEventStream } from "./eventStream";

const PATH = "/v1/businesses/business_1/events";
const URL_BASE = `https://cabinet.example/api/backend${PATH}`;

function streamRequest(headers: Record<string, string> = {}, signal?: AbortSignal): NextRequest {
  return new NextRequest(URL_BASE, { headers: { cookie: "aw_session=tok", ...headers }, signal });
}

function sseBody(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("the live event stream through the BFF", () => {
  it("is recognized by its path and method only", () => {
    expect(isEventStreamPath("GET", PATH)).toBe(true);
    expect(isEventStreamPath("POST", PATH)).toBe(false);
    expect(isEventStreamPath("GET", "/v1/businesses/business_1/events/x")).toBe(false);
    expect(isEventStreamPath("GET", "/v1/businesses/business_1/attention-counts")).toBe(false);
  });

  it("passes the stream on unbuffered with the session and the last event id", async () => {
    const fetchMock = vi.fn(async (_url: string, _init: RequestInit) =>
      new Response(sseBody(["event: stream.ready\ndata: {}\n\n", ": heartbeat\n\n"]), {
        headers: { "content-type": "text/event-stream; charset=utf-8", "cache-control": "no-cache" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await relayEventStream(streamRequest({ "last-event-id": "01790812800000000-0000abcd" }), PATH);

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toMatch(/^text\/event-stream/);
    expect(response.headers.get("cache-control")).toBe("no-cache, no-transform");
    expect(response.headers.get("x-accel-buffering")).toBe("no");
    expect(await response.text()).toBe("event: stream.ready\ndata: {}\n\n: heartbeat\n\n");
    const [url, init] = fetchMock.mock.calls[0]!;
    const sent = new Headers(init.headers);
    expect(url).toMatch(/\/v1\/businesses\/business_1\/events$/);
    expect(sent.get("authorization")).toBe("Bearer tok");
    expect(sent.get("last-event-id")).toBe("01790812800000000-0000abcd");
    expect(sent.get("accept")).toBe("text/event-stream");
  });

  it("ends the call to the API when the browser goes away", async () => {
    let upstreamSignal: AbortSignal | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_url: string, init: RequestInit) => {
        upstreamSignal = init.signal ?? undefined;
        return new Response(sseBody([]), { headers: { "content-type": "text/event-stream" } });
      }),
    );
    const browser = new AbortController();

    await relayEventStream(streamRequest({}, browser.signal), PATH);
    browser.abort();

    expect(upstreamSignal?.aborted).toBe(true);
  });

  it("answers 504 when the API does not start answering in time", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url: string, init: RequestInit) =>
          new Promise<Response>((_resolve, reject) => {
            init.signal?.addEventListener("abort", () => reject(new Error("aborted")));
          }),
      ),
    );

    const response = await relayEventStream(streamRequest(), PATH, 10);

    expect(response.status).toBe(504);
    expect((await response.json()) as unknown).toMatchObject({ error: "backend_unavailable" });
  });

  it("answers 502 when the API is down and drops a rejected session", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("fetch failed"))));
    expect((await relayEventStream(streamRequest(), PATH)).status).toBe(502);

    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json({ error: "authentication_required", message: "Expired." }, { status: 401 })),
    );
    const refused = await relayEventStream(streamRequest(), PATH);
    expect(refused.status).toBe(401);
    expect(refused.headers.get("set-cookie")).toMatch(/aw_session=;/);
    expect(refused.headers.get("x-accel-buffering")).toBeNull();
  });

  it("keeps the API's own headers on an answer that is not a stream", () => {
    const headers = eventStreamHeaders(new Headers({ "content-type": "application/json" }), "req-1");

    expect(headers.get("x-request-id")).toBe("req-1");
    expect(headers.get("cache-control")).toBe("no-store");
    expect(headers.get("x-accel-buffering")).toBeNull();
  });
});

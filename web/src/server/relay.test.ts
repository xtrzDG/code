import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DEFAULT_BODY_LIMIT_BYTES } from "./bodyLimits";
import { relayToBackend } from "./relay";

const URL_BASE = "https://cabinet.example/api/backend/v1/businesses/biz_1/profile";

function streamOf(size: number): ReadableStream<Uint8Array> {
  let sent = 0;
  return new ReadableStream({
    pull(controller) {
      if (sent >= size) {
        controller.close();
        return;
      }
      const chunk = new Uint8Array(Math.min(64 * 1024, size - sent));
      sent += chunk.byteLength;
      controller.enqueue(chunk);
    },
  });
}

/** The API, reading the whole body as fetch would. */
function stubApi() {
  const received: number[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (_url: string, init: RequestInit) => {
      const body = init.body ? await new Response(init.body as BodyInit).arrayBuffer() : new ArrayBuffer(0);
      received.push(body.byteLength);
      return Response.json({ ok: true });
    }),
  );
  return received;
}

function post(body: BodyInit, headers: Record<string, string> = {}): NextRequest {
  return new NextRequest(URL_BASE, {
    method: "PATCH",
    body,
    headers: { "content-type": "application/json", cookie: "aw_session=tok", ...headers },
    // Node's fetch needs half-duplex for a streamed body.
    duplex: "half",
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("relayToBackend body limits", () => {
  it("forwards a body within the limit", async () => {
    const received = stubApi();

    const response = await relayToBackend(post("x".repeat(1000)), "/v1/businesses/biz_1/profile", { useSession: true });

    expect(response.status).toBe(200);
    expect(received).toEqual([1000]);
  });

  it("refuses a declared length over the limit without calling the API", async () => {
    const received = stubApi();

    const response = await relayToBackend(post("x".repeat(DEFAULT_BODY_LIMIT_BYTES + 1)), "/v1/businesses/biz_1/profile", {
      useSession: true,
    });

    expect(response.status).toBe(413);
    expect(await response.json()).toEqual({
      error: "payload_too_large",
      message: "The request body is larger than the 256 KB allowed here.",
    });
    expect(received).toEqual([]);
  });

  it("cuts a streamed body that grows over the limit", async () => {
    stubApi();

    const response = await relayToBackend(post(streamOf(DEFAULT_BODY_LIMIT_BYTES * 2)), "/v1/businesses/biz_1/profile", {
      useSession: true,
    });

    expect(response.status).toBe(413);
    expect((await response.json()).error).toBe("payload_too_large");
  });
});

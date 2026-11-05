import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

const DSN = "https://public@o1.ingest.sentry.io/42";
const ENVELOPE = `${JSON.stringify({ dsn: DSN, event_id: "e1" })}\n{"type":"event"}\n{}`;

function envelope(body: BodyInit, headers: Record<string, string> = { "sec-fetch-site": "same-origin" }): Request {
  return new Request("https://cabinet.example/api/monitoring", { method: "POST", body, headers });
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("POST /api/monitoring", () => {
  it("forwards an envelope from the site's own pages", async () => {
    vi.stubEnv("SENTRY_DSN", DSN);
    const fetchMock = vi.fn(async () => new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(envelope(ENVELOPE));

    expect(response.status).toBe(204);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("refuses another site's envelopes", async () => {
    vi.stubEnv("SENTRY_DSN", DSN);
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    expect((await POST(envelope(ENVELOPE, { "sec-fetch-site": "cross-site" }))).status).toBe(403);
    expect((await POST(envelope(ENVELOPE, {}))).status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("refuses an envelope over 256 KB, also one that does not declare its length", async () => {
    vi.stubEnv("SENTRY_DSN", DSN);
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const big = `${ENVELOPE}${"x".repeat(256 * 1024)}`;

    const declared = await POST(envelope(big, { "sec-fetch-site": "same-origin", "content-length": String(big.length) }));
    const streamed = await POST(
      new Request("https://cabinet.example/api/monitoring", {
        method: "POST",
        body: new ReadableStream({
          start(controller) {
            controller.enqueue(new TextEncoder().encode(big));
            controller.close();
          },
        }),
        headers: { "sec-fetch-site": "same-origin" },
        duplex: "half",
      } as RequestInit),
    );

    expect(declared.status).toBe(413);
    expect(streamed.status).toBe(413);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

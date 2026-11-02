import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

function change(body: BodyInit, headers: Record<string, string> = {}): NextRequest {
  return new NextRequest("https://cabinet.example/api/locale", {
    method: "POST",
    body,
    headers: { "content-type": "application/json", "sec-fetch-site": "same-origin", ...headers },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("POST /api/locale", () => {
  it("switches the interface language in a cookie", async () => {
    const response = await POST(change(JSON.stringify({ locale: "it" })));

    expect(response.status).toBe(204);
    expect(response.headers.get("set-cookie")).toContain("aw_locale=it");
  });

  it("saves it in a signed-in user's account", async () => {
    const fetchMock = vi.fn(async () => Response.json({}));
    vi.stubGlobal("fetch", fetchMock);

    await POST(change(JSON.stringify({ locale: "en" }), { cookie: "aw_session=tok" }));

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toMatch(/\/v1\/me$/);
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe(JSON.stringify({ locale: "en" }));
  });

  it("refuses a body over 1 KB without reading it in full", async () => {
    const declared = await POST(change(JSON.stringify({ locale: "it", pad: "x".repeat(2000) })));
    const streamed = await POST(
      new NextRequest("https://cabinet.example/api/locale", {
        method: "POST",
        body: new ReadableStream({
          start(controller) {
            controller.enqueue(new TextEncoder().encode(`{"locale":"it","pad":"${"x".repeat(4096)}"}`));
            controller.close();
          },
        }),
        headers: { "content-type": "application/json", "sec-fetch-site": "same-origin" },
        duplex: "half",
      }),
    );

    expect(declared.status).toBe(413);
    expect(streamed.status).toBe(413);
    expect((await streamed.json()).error).toBe("payload_too_large");
  });

  it("refuses an unknown language, a broken body and another site", async () => {
    expect((await POST(change(JSON.stringify({ locale: "xx" })))).status).toBe(422);
    expect((await POST(change("not json"))).status).toBe(422);
    expect((await POST(change(JSON.stringify({ locale: "it" }), { "sec-fetch-site": "cross-site" }))).status).toBe(403);
  });
});

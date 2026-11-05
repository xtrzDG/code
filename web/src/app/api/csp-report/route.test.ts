import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const REPORT = JSON.stringify({
  "csp-report": {
    "document-uri": "https://cabinet.example.com/b/business_1/overview?view=all",
    "effective-directive": "style-src-attr",
    "blocked-uri": "inline",
    "script-sample": "color: red",
  },
});

async function loadRoute() {
  // The limiters live in the module: every test starts with fresh ones.
  vi.resetModules();
  return import("./route");
}

function report(body: string, headers: Record<string, string> = {}): Request {
  return new Request("https://cabinet.example.com/api/csp-report", {
    method: "POST",
    headers: { "content-type": "application/csp-report", ...headers },
    body,
  });
}

beforeEach(() => {
  vi.stubEnv("SITE_URL", "https://cabinet.example.com");
  vi.stubEnv("SENTRY_DSN", "https://public0000@o1.ingest.sentry.io/4500");
  vi.stubEnv("TRUSTED_PROXY_HOPS", "1");
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("POST /api/csp-report", () => {
  it("forwards a cleaned report to Sentry's security endpoint and answers 204", async () => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    const { POST } = await loadRoute();

    const response = await POST(report(REPORT));

    expect(response.status).toBe(204);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toMatch(/^https:\/\/o1\.ingest\.sentry\.io\/api\/4500\/security\/\?sentry_key=public0000/);
    const sent = JSON.parse(String(init.body))["csp-report"];
    expect(sent["document-uri"]).toBe("https://cabinet.example.com/b/business_1/overview");
    expect(sent).not.toHaveProperty("script-sample");
  });

  it("drops reports without a Sentry project, still with 204", async () => {
    vi.stubEnv("SENTRY_DSN", "");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const { POST } = await loadRoute();

    expect((await POST(report(REPORT))).status).toBe(204);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("answers 204 even when Sentry does not", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new Error("offline"))));
    const { POST } = await loadRoute();

    expect((await POST(report(REPORT))).status).toBe(204);
  });

  it("refuses other content, oversized and unreadable bodies", async () => {
    vi.stubGlobal("fetch", vi.fn());
    const { POST } = await loadRoute();

    expect((await POST(report(REPORT, { "content-type": "text/plain" }))).status).toBe(415);
    expect((await POST(report(REPORT, { "content-length": String(64 * 1024) }))).status).toBe(413);
    expect((await POST(report("x".repeat(17 * 1024)))).status).toBe(413);
    expect((await POST(report("not json"))).status).toBe(400);
  });

  it("limits each client, apart from the others", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 201 })));
    const { POST } = await loadRoute();
    const from = (address: string) => report(REPORT, { "x-forwarded-for": address });

    const answers = [];
    for (let index = 0; index < 31; index += 1) {
      answers.push((await POST(from("198.51.100.7"))).status);
    }

    expect(answers.slice(0, 30).every((status) => status === 204)).toBe(true);
    expect(answers[30]).toBe(429);
    expect((await POST(from("203.0.113.9"))).status).toBe(204);
  });
});

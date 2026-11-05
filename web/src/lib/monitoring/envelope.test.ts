import { describe, expect, it, vi } from "vitest";

import { createClientReporter, MAX_CLIENT_REPORTS, type BrowserSentry } from "./clientReporter";
import { createWindowLimiter, envelopeUrl, parseDsn, readdressEnvelope } from "./envelope";
import { TUNNEL_PATH, TUNNEL_PLACEHOLDER_DSN } from "./options";

const DSN = "https://publickey@o1.ingest.de.sentry.io/4507";

describe("envelopes through the tunnel", () => {
  it("goes to the envelope endpoint of the configured project", () => {
    const parsed = parseDsn(DSN);

    expect(parsed).toEqual({ origin: "https://o1.ingest.de.sentry.io", projectId: "4507" });
    expect(envelopeUrl(parsed!)).toBe("https://o1.ingest.de.sentry.io/api/4507/envelope/");
    expect(parseDsn("not a url")).toBeNull();
    expect(parseDsn("https://sentry.example/4507")).toBeNull();
    expect(parseDsn("ftp://key@sentry.example/4507")).toBeNull();
    expect(parseDsn("https://key@sentry.example/project")).toBeNull();
  });

  it("puts the configured DSN in the header and keeps the items", () => {
    const body = `${JSON.stringify({ dsn: TUNNEL_PLACEHOLDER_DSN, sent_at: "now" })}\n{"type":"event"}\n{"x":1}`;

    const readdressed = readdressEnvelope(body, DSN);

    const [header, ...items] = (readdressed ?? "").split("\n");
    expect(JSON.parse(header ?? "")).toEqual({ dsn: DSN, sent_at: "now" });
    expect(items).toEqual(['{"type":"event"}', '{"x":1}']);
  });

  it("refuses what is not an envelope", () => {
    expect(readdressEnvelope("no newline", DSN)).toBeNull();
    expect(readdressEnvelope("[1]\n{}", DSN)).toBeNull();
    expect(readdressEnvelope("{broken\n{}", DSN)).toBeNull();
    expect(readdressEnvelope("\n{}", DSN)).toBeNull();
  });

  it("forwards a limited number per window", () => {
    let now = 0;
    const tryAcquire = createWindowLimiter(2, 1_000, () => now);

    expect([tryAcquire(), tryAcquire(), tryAcquire()]).toEqual([true, true, false]);
    now = 1_000;
    expect(tryAcquire()).toBe(true);
  });
});

function fakeSentry(): BrowserSentry & { captured: unknown[]; options: Record<string, unknown>[] } {
  const captured: unknown[] = [];
  const options: Record<string, unknown>[] = [];
  return {
    captured,
    options,
    init: (value) => options.push(value),
    captureException: (error) => captured.push(error),
    dedupeIntegration: () => "dedupe",
    linkedErrorsIntegration: () => "linked",
  };
}

describe("browser error reports", () => {
  it("loads Sentry once, on the first error, through the tunnel", async () => {
    const sentry = fakeSentry();
    const load = vi.fn(async () => sentry);
    const report = createClientReporter(load, "production");

    expect(load).not.toHaveBeenCalled();
    expect(await report(new TypeError("x is undefined"))).toBe(true);
    expect(await report(new RangeError("too far"))).toBe(true);

    expect(load).toHaveBeenCalledTimes(1);
    expect(sentry.options).toEqual([
      expect.objectContaining({
        dsn: TUNNEL_PLACEHOLDER_DSN,
        tunnel: TUNNEL_PATH,
        environment: "production",
        defaultIntegrations: false,
        integrations: ["dedupe", "linked"],
        sendDefaultPii: false,
      }),
    ]);
    expect(sentry.captured).toHaveLength(2);
  });

  it("sends each error once and only a few per page", async () => {
    const sentry = fakeSentry();
    const report = createClientReporter(async () => sentry, "production");

    expect(await report("same")).toBe(true);
    expect(await report("same")).toBe(false);
    for (let index = 1; index < MAX_CLIENT_REPORTS + 3; index += 1) {
      await report(new Error(`error ${index}`));
    }

    expect(sentry.captured).toHaveLength(MAX_CLIENT_REPORTS);
  });

  it("gives up quietly when the SDK cannot be loaded", async () => {
    const report = createClientReporter(async () => {
      throw new Error("chunk load failed");
    }, "production");

    expect(await report(new Error("first"))).toBe(false);
    expect(await report(new Error("second"))).toBe(false);
  });
});

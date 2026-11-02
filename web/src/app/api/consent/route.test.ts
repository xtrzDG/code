import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ATTRIBUTION_COOKIE, decodeAttribution } from "@/lib/attribution";

import { POST } from "./route";

const CONSENT = "https://cabinet.example/api/consent";

function answer(body: unknown, headers: Record<string, string> = {}): NextRequest {
  return new NextRequest(CONSENT, {
    method: "POST",
    body: typeof body === "string" ? body : JSON.stringify(body),
    headers: { "content-type": "application/json", "sec-fetch-site": "same-origin", ...headers },
  });
}

const RECEIPT = "[A-Za-z0-9_-]{22}";
/** What the route wrote to the server's standard output. */
const written: string[] = [];

beforeEach(() => {
  written.length = 0;
  vi.spyOn(process.stdout, "write").mockImplementation((chunk: string | Uint8Array) => {
    written.push(String(chunk));
    return true;
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

/** The consent records the route wrote to the server's log. */
function consentLines(): Record<string, unknown>[] {
  return written
    .filter((line) => line.includes('"cookie_consent"'))
    .map((line) => JSON.parse(line) as Record<string, unknown>);
}

function setCookie(response: Response, name: string): string | undefined {
  return response.headers
    .getSetCookie()
    .find((line) => line.startsWith(`${name}=`));
}

describe("POST /api/consent", () => {
  it("stores an acceptance for six months and keeps where the visitor came from", async () => {
    const response = await POST(
      answer({ choice: "granted", page: "/it?utm_source=instagram&ref=FRIEND1", referrer: "https://www.instagram.com/p/x" }),
    );

    expect(response.status).toBe(204);
    expect(setCookie(response, "aw_consent")).toMatch(new RegExp(`^aw_consent=1\\.granted\\.${RECEIPT}; .*Max-Age=15811200`));
    const attribution = setCookie(response, ATTRIBUTION_COOKIE)?.split(";")[0]?.split("=")[1];
    expect(decodeAttribution(attribution)).toMatchObject({
      utm_source: "instagram",
      referral_code: "FRIEND1",
      referrer_host: "www.instagram.com",
      landing_path: "/it",
    });
  });

  it("keeps the first touch a visitor already has, and none for signed-in people or other pages", async () => {
    const cases = [
      answer({ choice: "granted", page: "/it?utm_source=b" }, { cookie: `${ATTRIBUTION_COOKIE}=first` }),
      answer({ choice: "granted", page: "/it" }, { cookie: "aw_session=tok" }),
      answer({ choice: "granted", page: "/login?utm_source=x" }),
      answer({ choice: "granted", page: "//evil.example/it" }),
      answer({ choice: "granted", page: "https://evil.example/it" }),
      answer({ choice: "granted" }),
    ];
    for (const request of cases) {
      const response = await POST(request);
      expect(response.status).toBe(204);
      expect(setCookie(response, "aw_consent")).toMatch(/^aw_consent=1\.granted/);
      expect(setCookie(response, ATTRIBUTION_COOKIE)).toBeUndefined();
    }
  });

  it("stores a rejection and drops the attribution cookie", async () => {
    const response = await POST(answer({ choice: "denied", page: "/it?utm_source=x" }, { cookie: `${ATTRIBUTION_COOKIE}=old` }));

    expect(response.status).toBe(204);
    expect(setCookie(response, "aw_consent")).toMatch(/^aw_consent=1\.denied/);
    expect(setCookie(response, ATTRIBUTION_COOKIE)).toMatch(/^aw_attr=; .*Max-Age=0/);
  });

  it("refuses another site's answer, a body over 4 KB and anything but a choice", async () => {
    const foreign = await POST(answer({ choice: "granted" }, { "sec-fetch-site": "cross-site", origin: "https://evil.example" }));
    const silent = await POST(
      new NextRequest(CONSENT, { method: "POST", body: JSON.stringify({ choice: "granted" }), headers: { "content-type": "application/json" } }),
    );
    const large = await POST(answer({ choice: "granted", page: `/it?${"x".repeat(5000)}` }));

    expect(foreign.status).toBe(403);
    expect(silent.status).toBe(403);
    expect(setCookie(foreign, "aw_consent")).toBeUndefined();
    expect(large.status).toBe(413);
    expect((await POST(answer({ choice: "maybe" }))).status).toBe(422);
    expect((await POST(answer("not json"))).status).toBe(422);
  });

  it("logs each answer on the server with its version, time and receipt id, nothing about who", async () => {
    const before = Date.now();
    const response = await POST(
      answer({ choice: "granted", page: "/it?utm_source=x", referrer: "https://www.instagram.com/" }, { "x-forwarded-for": "203.0.113.7" }),
    );

    const [line] = consentLines();
    expect(consentLines()).toHaveLength(1);
    expect(Object.keys(line ?? {}).sort()).toEqual(["at", "choice", "consent_id", "event", "version"]);
    expect(line).toMatchObject({ event: "cookie_consent", choice: "granted", version: "1" });
    expect(Date.parse(String(line?.at))).toBeGreaterThanOrEqual(before - 1000);
    expect(setCookie(response, "aw_consent")).toContain(`1.granted.${String(line?.consent_id)};`);
    expect(JSON.stringify(line)).not.toMatch(/203\.0\.113|instagram|utm_source/);
  });

  it("keeps the receipt id when the visitor changes their mind", async () => {
    const receipt = "AAECAwQFBgcICQoLDA0ODw";
    const response = await POST(answer({ choice: "denied" }, { cookie: `aw_consent=1.granted.${receipt}` }));

    expect(setCookie(response, "aw_consent")).toMatch(new RegExp(`^aw_consent=1\\.denied\\.${receipt};`));
    expect(consentLines()).toEqual([expect.objectContaining({ choice: "denied", consent_id: receipt })]);
  });

  it("logs nothing for a refused answer", async () => {
    await POST(answer({ choice: "granted" }, { "sec-fetch-site": "cross-site", origin: "https://evil.example" }));
    await POST(answer({ choice: "maybe" }));

    expect(consentLines()).toEqual([]);
  });
});

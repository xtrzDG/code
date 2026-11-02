import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

const ROTATE = "https://cabinet.example/api/auth/session/rotate";
const ROTATED = {
  access_token: "fresh-token",
  expires_at: 1_790_000_000_000_000,
  user: { id: "user_1", locale: "it" },
  is_new_user: false,
  auth_level: "two_factor",
  recovery_codes: [],
};

function rotate(headers: Record<string, string> = {}): NextRequest {
  return new NextRequest(ROTATE, {
    method: "POST",
    headers: { cookie: "aw_session=old-token", "sec-fetch-site": "same-origin", ...headers },
  });
}

function answering(status: number, body: unknown) {
  return vi.fn(async () => Response.json(body, { status }));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("POST /api/auth/session/rotate", () => {
  it("swaps the session's token for the API's new one, never showing it", async () => {
    const fetchMock = answering(200, ROTATED);
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(rotate());

    expect(response.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toMatch(/\/v1\/auth\/session\/rotate$/);
    expect(init.method).toBe("POST");
    expect(new Headers(init.headers).get("authorization")).toBe("Bearer old-token");
    expect(response.headers.get("set-cookie")).toContain("fresh-token");
    const body = (await response.json()) as Record<string, unknown>;
    expect(body.auth_level).toBe("two_factor");
    expect(JSON.stringify(body)).not.toContain("fresh-token");
  });

  it("passes a refusal on and keeps the cookie, unless the session is gone", async () => {
    vi.stubGlobal("fetch", answering(409, { error: "conflict", message: "Confirm it is you first." }));
    const kept = await POST(rotate());
    vi.stubGlobal("fetch", answering(401, { error: "authentication_required", message: "Sign in again." }));
    const gone = await POST(rotate());

    expect(kept.status).toBe(409);
    expect(kept.headers.get("set-cookie")).toBeNull();
    expect(gone.status).toBe(401);
    expect(gone.headers.get("set-cookie")).toContain("aw_session=;");
  });

  it("asks nothing without a session or for another site", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const signedOut = await POST(
      new NextRequest(ROTATE, { method: "POST", headers: { "sec-fetch-site": "same-origin" } }),
    );
    const crossSite = await POST(rotate({ "sec-fetch-site": "cross-site", origin: "https://evil.example" }));

    expect(signedOut.status).toBe(401);
    expect(crossSite.status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("says the API is out of reach without touching the cookie", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new Error("down"))));

    const response = await POST(rotate());

    expect(response.status).toBe(502);
    expect(response.headers.get("set-cookie")).toBeNull();
  });
});

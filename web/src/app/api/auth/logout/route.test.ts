import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

const LOGOUT = "https://cabinet.example/api/auth/logout";

function logout(headers: Record<string, string>): NextRequest {
  return new NextRequest(LOGOUT, { method: "POST", headers: { cookie: "aw_session=tok", ...headers } });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("POST /api/auth/logout", () => {
  it("ends the session, drops the cookie and asks the browser to forget the site's data", async () => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(logout({ "sec-fetch-site": "same-origin" }));

    expect(response.status).toBe(204);
    expect(response.headers.get("clear-site-data")).toBe('"cache", "cookies", "storage"');
    expect(response.headers.get("cache-control")).toBe("no-store");
    expect(response.headers.get("set-cookie")).toContain("aw_session=;");
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toMatch(/\/v1\/auth\/logout$/);
    expect(new Headers(init.headers).get("authorization")).toBe("Bearer tok");
  });

  it("clears the site's data even when the API is out of reach", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new Error("down"))));

    const response = await POST(logout({ "sec-fetch-site": "same-origin" }));

    expect(response.status).toBe(204);
    expect(response.headers.get("clear-site-data")).toBe('"cache", "cookies", "storage"');
  });

  it("refuses another site's sign-out request", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(logout({ "sec-fetch-site": "cross-site", origin: "https://evil.example" }));

    expect(response.status).toBe(403);
    expect(response.headers.get("clear-site-data")).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

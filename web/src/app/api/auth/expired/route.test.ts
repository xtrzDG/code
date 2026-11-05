import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

const EXPIRED = "https://cabinet.example/api/auth/expired?next=/b/biz_1/bookings";

function request(cookie?: string): NextRequest {
  return new NextRequest(EXPIRED, {
    headers: { "sec-fetch-site": "cross-site", ...(cookie ? { cookie } : {}) },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("GET /api/auth/expired", () => {
  it("keeps a session the API still accepts (a cross-site link cannot sign the owner out)", async () => {
    const fetchMock = vi.fn(async () => Response.json({ user: {} }));
    vi.stubGlobal("fetch", fetchMock);

    const response = await GET(request("aw_session=valid-token"));

    expect(response.headers.get("set-cookie")).toBeNull();
    expect(response.headers.get("location")).toBe("https://cabinet.example/b/biz_1/bookings");
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toMatch(/\/v1\/me$/);
    expect(new Headers(init.headers).get("authorization")).toBe("Bearer valid-token");
  });

  it("keeps the session when the API cannot be reached", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("down");
      }),
    );

    const response = await GET(request("aw_session=valid-token"));

    expect(response.headers.get("set-cookie")).toBeNull();
  });

  it("drops a session the API rejects and opens the sign-in page", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 401 })));

    const response = await GET(request("aw_session=old-token"));

    expect(response.headers.get("set-cookie")).toMatch(/aw_session=;.*Max-Age=0/i);
    expect(response.headers.get("location")).toBe(
      "https://cabinet.example/login?next=%2Fb%2Fbiz_1%2Fbookings&reason=expired",
    );
  });

  it("opens the sign-in page without a session, without calling the API", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await GET(request());

    expect(fetchMock).not.toHaveBeenCalled();
    expect(response.headers.get("location")).toContain("/login?");
  });
});

import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { calendarReturnPath, readCalendarCallback } from "@/server/calendarCompletion";

import { GET } from "./route";

const CALLBACK = "https://cabinet.example/integrations/google-calendar/callback?code=good-code&state=s1";

function callback(cookie?: string): NextRequest {
  return new NextRequest(CALLBACK, { headers: cookie ? { cookie } : {} });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("calendar completion helpers", () => {
  it("reads only the non-blank callback values", () => {
    expect(readCalendarCallback(new URLSearchParams("code=c&state=s&error=%20&x=1"))).toEqual({ code: "c", state: "s" });
  });

  it("returns to the business's Channels page, or to the businesses list", () => {
    expect(calendarReturnPath({ business_id: "biz_1", connection: { calendar_id: "primary" } })).toBe(
      "/b/biz_1/assistant/channels?calendar=connected",
    );
    expect(calendarReturnPath({ business_id: "biz_1", failure: "access_denied" })).toBe(
      "/b/biz_1/assistant/channels?calendar=error&reason=access_denied",
    );
    expect(calendarReturnPath({ business_id: null, failure: "link_expired" })).toBe(
      "/businesses?calendar=error&reason=link_expired",
    );
    expect(calendarReturnPath(null)).toBe("/businesses?calendar=error&reason=provider_error");
  });
});

describe("GET /integrations/google-calendar/callback", () => {
  it("finishes connecting with the owner's session", async () => {
    const fetchMock = vi.fn(async () =>
      Response.json({ business_id: "biz_1", connection: { calendar_id: "primary" }, failure: null }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await GET(callback("aw_session=tok_owner"));

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe("https://cabinet.example/b/biz_1/assistant/channels?calendar=connected");
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toMatch(/\/v1\/integrations\/google-calendar\/complete$/);
    expect(init.method).toBe("POST");
    expect(new Headers(init.headers).get("authorization")).toBe("Bearer tok_owner");
    expect(JSON.parse(String(init.body))).toEqual({ code: "good-code", state: "s1" });
  });

  it("asks for sign-in first, without calling the API", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await GET(callback());

    expect(fetchMock).not.toHaveBeenCalled();
    expect(response.headers.get("location")).toBe(
      "https://cabinet.example/login?next=%2Fintegrations%2Fgoogle-calendar%2Fcallback%3Fcode%3Dgood-code%26state%3Ds1",
    );
  });

  it("reports a foreign link as expired, without its business", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json({ business_id: null, connection: null, failure: "link_expired" })),
    );

    const response = await GET(callback("aw_session=tok_victim"));

    expect(response.headers.get("location")).toBe("https://cabinet.example/businesses?calendar=error&reason=link_expired");
  });
});

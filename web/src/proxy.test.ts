import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { proxy } from "./proxy";

const RETURN_URL = "https://app.example.com/b/biz_1/billing?checkout=return";

describe("proxy", () => {
  it("turns the payment page's cross-site form POST into a GET that carries the session", async () => {
    const request = new NextRequest(RETURN_URL, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: "order_status=approved&signature=x",
    });

    const response = await proxy(request);

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe(RETURN_URL);
  });

  it("leaves Server Action POSTs alone", async () => {
    const request = new NextRequest(RETURN_URL, {
      method: "POST",
      headers: { "next-action": "abc", cookie: "aw_session=tok; aw_locale=en" },
      body: "[]",
    });

    const response = await proxy(request);

    expect(response.status).not.toBe(303);
  });

  it("still sends visitors without a session to sign in", async () => {
    const response = await proxy(new NextRequest(RETURN_URL));

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe(
      "https://app.example.com/login?next=%2Fb%2Fbiz_1%2Fbilling%3Fcheckout%3Dreturn",
    );
  });

  it("sends visitors opening a notification link to sign in first, then back to it", async () => {
    const response = await proxy(new NextRequest("https://app.example.com/n/AQID_token-text"));

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("https://app.example.com/login?next=%2Fn%2FAQID_token-text");
  });
});

describe("proxy on the hosted chat page", () => {
  const VIEW = {
    business_id: "business_1",
    slug: "cafe-batumi",
    business_name: "Cafe Batumi",
    is_enabled: true,
    default_language: "en",
    languages: [{ tag: "en", native_name: "English", direction: "ltr" }],
    api_base_url: "https://api.workshop.example",
  };

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("moves the business id or an older address to the current one, keeping the tag", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json(VIEW)));

    const response = await proxy(new NextRequest("https://app.example.com/c/business_1?src=table"));

    expect(response.status).toBe(308);
    expect(response.headers.get("location")).toBe("https://app.example.com/c/cafe-batumi?src=table");
    expect(response.headers.get("x-robots-tag")).toBe("noindex, nofollow");
  });

  it("allows the API in the page's policy and hands the business to the page, signed in or not", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json(VIEW)));

    const response = await proxy(new NextRequest("https://app.example.com/c/cafe-batumi"));

    const policy = response.headers.get("content-security-policy") ?? "";
    expect(response.status).toBe(200);
    expect(policy).toContain("connect-src 'self' https://api.workshop.example");
    expect(policy).toContain("form-action 'none'");
    expect(response.headers.get("x-robots-tag")).toBe("noindex, nofollow");
    expect(response.headers.get("x-middleware-request-x-aw-hosted-chat")).toMatch(/^v1\./);
  });

  it("tells the page when nothing has the address", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ error: "not_found" }, { status: 404 })));

    const response = await proxy(new NextRequest("https://app.example.com/c/nobody"));

    expect(response.headers.get("x-middleware-request-x-aw-hosted-chat")).toBe("missing");
    expect(response.headers.get("content-security-policy")).toContain("connect-src 'self';");
  });

  it("keeps the privacy notice out of search engines without a lookup, and drops a forged business", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await proxy(
      new NextRequest("https://app.example.com/c/cafe-batumi/privacy", { headers: { "x-aw-hosted-chat": "v1.forged" } }),
    );

    expect(fetchMock).not.toHaveBeenCalled();
    expect(response.headers.get("x-robots-tag")).toBe("noindex, nofollow");
    expect(response.headers.get("x-middleware-request-x-aw-hosted-chat")).toBeNull();
  });
});

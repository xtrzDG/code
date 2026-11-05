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

describe("proxy on the public site", () => {
  it("sends a legal page without a language to the reader's", async () => {
    const response = await proxy(
      new NextRequest("https://app.example.com/privacy?from=footer", { headers: { "accept-language": "it-IT,it;q=0.9" } }),
    );

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("https://app.example.com/it/privacy?from=footer");
  });

  it("prefers the language cookie for that redirect", async () => {
    const response = await proxy(
      new NextRequest("https://app.example.com/terms", { headers: { cookie: "aw_locale=it", "accept-language": "en" } }),
    );

    expect(response.headers.get("location")).toBe("https://app.example.com/it/terms");
  });

  it("renders a public page in its own language and starts a new visitor's cabinet in it", async () => {
    const response = await proxy(new NextRequest("https://app.example.com/it/for/hotel", { headers: { "accept-language": "en" } }));

    expect(response.status).toBe(200);
    expect(response.headers.get("x-middleware-request-x-aw-path-locale")).toBe("it");
    expect(response.cookies.get("aw_locale")?.value).toBe("it");
  });

  it("keeps a returning visitor's language and lets no browser name the page's", async () => {
    const response = await proxy(
      new NextRequest("https://app.example.com/login", {
        headers: { cookie: "aw_locale=en", "x-aw-path-locale": "it" },
      }),
    );

    expect(response.cookies.get("aw_locale")).toBeUndefined();
    expect(response.headers.get("x-middleware-request-x-aw-path-locale")).toBeNull();
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

describe("proxy and the cookie choice", () => {
  it("keeps where a visitor came from only after they accepted it", async () => {
    const before = await proxy(new NextRequest("https://app.example.com/it?utm_source=newsletter"));
    const after = await proxy(
      new NextRequest("https://app.example.com/it?utm_source=newsletter", { headers: { cookie: "aw_consent=1.granted" } }),
    );

    expect(before.cookies.get("aw_attr")).toBeUndefined();
    expect(after.cookies.get("aw_attr")?.value).toBeTruthy();
  });

  it("drops an attribution cookie kept without consent, or after it was withdrawn", async () => {
    for (const cookie of ["aw_attr=old", "aw_attr=old; aw_consent=1.denied"]) {
      const response = await proxy(new NextRequest("https://app.example.com/it", { headers: { cookie } }));

      expect(response.cookies.get("aw_attr"), cookie).toMatchObject({ value: "", maxAge: 0 });
    }
  });
});

describe("proxy and the session cookie in production", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("never takes a session from the cookie's old name, and drops that cookie", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("BACKEND_URL", "http://api.internal:8000");

    const response = await proxy(new NextRequest("https://app.example.com/businesses", { headers: { cookie: "aw_session=planted" } }));

    // No session: sign in first.
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("https://app.example.com/login");
    expect(response.cookies.get("aw_session")).toMatchObject({ value: "", maxAge: 0 });
    expect(response.cookies.get("__Host-aw_session")).toBeUndefined();
  });

  it("keeps the session cookie Secure on a real host even with COOKIE_SECURE=false", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("COOKIE_SECURE", "false");
    vi.stubEnv("BACKEND_URL", "http://api.internal:8000");

    const real = await proxy(new NextRequest("https://app.example.com/businesses", { headers: { cookie: "aw_session=tok" } }));
    const local = await proxy(
      new NextRequest("http://localhost:3010/login", { headers: { cookie: "aw_session=tok", host: "localhost:3010" } }),
    );

    // On the real host the plain-HTTP name is not the session: sign in first.
    expect(real.status).toBe(307);
    // On this machine over plain HTTP it is (the e2e suite): a signed-in user leaves the sign-in page.
    expect(local.status).toBe(307);
    expect(local.headers.get("location")).toBe("http://localhost:3010/businesses");
  });
});

describe("proxy on the payment pages", () => {
  it("gives the billing page a policy with no third-party host; other pages keep Turnstile", async () => {
    const headers = { cookie: "aw_session=tok; aw_locale=en" };

    const billing = await proxy(new NextRequest("https://app.example.com/b/biz_1/settings/billing?card=return", { headers }));
    const overview = await proxy(new NextRequest("https://app.example.com/b/biz_1/overview", { headers }));

    const policy = billing.headers.get("content-security-policy") ?? "";
    expect(policy).toContain("script-src 'self' 'nonce-");
    expect(policy).not.toContain("challenges.cloudflare.com");
    // The page renders with the same policy it is sent with.
    expect(billing.headers.get("x-middleware-request-content-security-policy")).toBe(policy);
    expect(overview.headers.get("content-security-policy")).toContain("https://challenges.cloudflare.com");
  });
});

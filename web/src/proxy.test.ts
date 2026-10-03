import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

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

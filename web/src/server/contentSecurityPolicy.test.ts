import { describe, expect, it } from "vitest";

import { buildContentSecurityPolicy, buildHostedChatPolicy, createNonce } from "./contentSecurityPolicy";

function directives(policy: string): Map<string, string> {
  return new Map(
    policy.split("; ").map((directive) => {
      const [name, ...values] = directive.split(" ");
      return [name ?? "", values.join(" ")];
    }),
  );
}

describe("createNonce", () => {
  it("makes a fresh 128-bit base64 nonce every time", () => {
    const nonces = new Set(Array.from({ length: 50 }, () => createNonce()));
    expect(nonces.size).toBe(50);
    for (const nonce of nonces) {
      expect(nonce).toMatch(/^[A-Za-z0-9+/]{22}==$/);
    }
  });
});

describe("buildContentSecurityPolicy", () => {
  it("runs only nonce'd scripts and what they load, and allows Turnstile", () => {
    const policy = directives(buildContentSecurityPolicy({ nonce: "abc", isDevelopment: false, isHttps: true }));

    expect(policy.get("script-src")).toBe("'self' 'nonce-abc' 'strict-dynamic' https://challenges.cloudflare.com");
    expect(policy.get("default-src")).toBe("'self'");
    expect(policy.get("frame-src")).toBe("https://challenges.cloudflare.com");
    expect(policy.get("connect-src")).toBe("'self' https://challenges.cloudflare.com");
    expect(policy.get("frame-ancestors")).toBe("'none'");
    expect(policy.get("base-uri")).toBe("'none'");
    expect(policy.get("object-src")).toBe("'none'");
    expect(policy.get("form-action")).toBe("'self' https://pay.flitt.com");
    // A nonce in style-src would switch 'unsafe-inline' off for style attributes.
    expect(policy.get("style-src")).toBe("'self' 'unsafe-inline'");
    expect(policy.has("upgrade-insecure-requests")).toBe(true);
  });

  it("allows eval only in development and upgrades requests only over HTTPS", () => {
    const development = directives(buildContentSecurityPolicy({ nonce: "n", isDevelopment: true, isHttps: false }));

    expect(development.get("script-src")).toContain("'unsafe-eval'");
    expect(development.has("upgrade-insecure-requests")).toBe(false);
  });
});

describe("buildHostedChatPolicy", () => {
  it("lets the hosted chat page talk only to itself and the API, with nothing framed or posted", () => {
    const policy = directives(
      buildHostedChatPolicy({ nonce: "abc", apiOrigin: "https://api.example", isDevelopment: false, isHttps: true }),
    );

    expect(policy.get("script-src")).toBe("'self' 'nonce-abc' 'strict-dynamic'");
    expect(policy.get("connect-src")).toBe("'self' https://api.example");
    expect(policy.get("frame-src")).toBe("'none'");
    expect(policy.get("form-action")).toBe("'none'");
    expect(policy.get("frame-ancestors")).toBe("'none'");
    expect(policy.has("upgrade-insecure-requests")).toBe(true);
  });

  it("leaves the API out when it is unknown and allows eval only in development", () => {
    const policy = directives(buildHostedChatPolicy({ nonce: "n", apiOrigin: null, isDevelopment: true, isHttps: false }));

    expect(policy.get("connect-src")).toBe("'self'");
    expect(policy.get("script-src")).toContain("'unsafe-eval'");
    expect(policy.has("upgrade-insecure-requests")).toBe(false);
  });
});

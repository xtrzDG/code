import { runInNewContext } from "node:vm";

import { describe, expect, it } from "vitest";

import { installTrustedTypesPolicy, TRUSTED_SCRIPT_ORIGINS, trustedTypesBootstrap, type TrustedTypesWindow } from "./trustedTypes";

interface Rules {
  createHTML: (value: string) => string | null;
  createScript: (value: string) => string | null;
  createScriptURL: (value: string) => string | null;
}

/** A browser with Trusted Types that remembers the policies made on it. */
function browser(origin = "https://cabinet.example.com") {
  const policies = new Map<string, Rules>();
  const win: TrustedTypesWindow = {
    trustedTypes: {
      createPolicy: (name, rules) => {
        policies.set(name, rules);
        return rules;
      },
    },
    location: { origin },
    document: { baseURI: `${origin}/b/business_1/overview` },
  };
  return { win, policies };
}

function installedRules(): Rules {
  const { win, policies } = browser();
  installTrustedTypesPolicy(win, TRUSTED_SCRIPT_ORIGINS);
  const rules = policies.get("default");
  if (!rules) {
    throw new Error("no default policy");
  }
  return rules;
}

describe("the Trusted Types default policy", () => {
  it("lets through text that cannot make an element, and React's empty script", () => {
    const rules = installedRules();

    expect(rules.createHTML('{"@context":"https://schema.org"}')).toBe('{"@context":"https://schema.org"}');
    expect(rules.createHTML("<script></script>")).toBe("<script></script>");
    expect(rules.createHTML("<img src=x onerror=alert(1)>")).toBeNull();
  });

  it("runs only JSON as script text", () => {
    const rules = installedRules();

    expect(rules.createScript(' {"a": 1} ')).toBe(' {"a": 1} ');
    expect(rules.createScript("[1, 2]")).toBe("[1, 2]");
    expect(rules.createScript("{ alert(1) }")).toBeNull();
    expect(rules.createScript("alert(1)")).toBeNull();
  });

  it("loads scripts from the page's origin and the listed ones only", () => {
    const rules = installedRules();

    expect(rules.createScriptURL("/_next/static/chunks/app.js")).toBe("https://cabinet.example.com/_next/static/chunks/app.js");
    expect(rules.createScriptURL("https://challenges.cloudflare.com/turnstile/v0/api.js")).toBe(
      "https://challenges.cloudflare.com/turnstile/v0/api.js",
    );
    expect(rules.createScriptURL("https://evil.example/x.js")).toBeNull();
    expect(rules.createScriptURL("javascript:alert(1)")).toBeNull();
    expect(rules.createScriptURL("http://[bad")).toBeNull();
  });

  it("does nothing without Trusted Types or when a default policy exists", () => {
    const bare = { location: { origin: "https://x" }, document: { baseURI: "https://x/" } };
    expect(() => installTrustedTypesPolicy(bare, [])).not.toThrow();

    const { win, policies } = browser();
    win.trustedTypes = { ...win.trustedTypes!, defaultPolicy: {}, createPolicy: win.trustedTypes!.createPolicy };
    installTrustedTypesPolicy(win, []);
    expect(policies.size).toBe(0);
  });
});

describe("trustedTypesBootstrap", () => {
  it("is a self-contained script that installs the policy and cannot close its element", () => {
    const source = trustedTypesBootstrap();
    const { win, policies } = browser();

    runInNewContext(source, { window: win, URL, JSON });

    expect(source).not.toContain("</");
    expect(policies.get("default")?.createScriptURL("https://challenges.cloudflare.com/a.js")).toBe("https://challenges.cloudflare.com/a.js");
  });
});

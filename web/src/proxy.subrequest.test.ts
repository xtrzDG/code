/**
 * CVE-2025-29927 and CVE-2025-55182 (WEB-05): a request that carries the
 * header Next.js once trusted to skip the middleware still meets the
 * proxy's sign-in redirect and Content Security Policy, and the header is
 * never forwarded to a page; the installed Next.js and React are past the
 * fixes of both advisories. The end-to-end suite asks the running build the
 * same (e2e/security.spec.ts, "the middleware bypass header").
 */

import { readFileSync } from "node:fs";
import path from "node:path";

import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { proxy } from "./proxy";
import { MIDDLEWARE_SUBREQUEST_HEADER } from "./server/middlewareSubrequest";

/** The values the published exploits send: the middleware's module name, repeated past the recursion limit. */
const BYPASS_VALUES = [
  "middleware",
  "src/middleware",
  "middleware:middleware:middleware:middleware:middleware",
  "src/middleware:src/middleware:src/middleware:src/middleware:src/middleware",
  "proxy:proxy:proxy:proxy:proxy",
  "src/proxy:src/proxy:src/proxy:src/proxy:src/proxy",
];
const FORWARDED = "x-middleware-request-";

function forwardedNames(response: Response): string[] {
  return (response.headers.get("x-middleware-override-headers") ?? "").split(",");
}

describe("the middleware bypass header", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("does not take a visitor without a session past the sign-in redirect", async () => {
    for (const value of BYPASS_VALUES) {
      const response = await proxy(
        new NextRequest("https://app.example.com/b/biz_1/settings/billing", {
          headers: { [MIDDLEWARE_SUBREQUEST_HEADER]: value },
        }),
      );

      expect(response.status, value).toBe(307);
      expect(response.headers.get("location"), value).toBe(
        "https://app.example.com/login?next=%2Fb%2Fbiz_1%2Fsettings%2Fbilling",
      );
    }
  });

  it("does not take a page past its policy, and never reaches the page", async () => {
    for (const value of BYPASS_VALUES) {
      const response = await proxy(
        new NextRequest("https://app.example.com/b/biz_1/overview", {
          headers: { cookie: "aw_session=tok; aw_locale=en", [MIDDLEWARE_SUBREQUEST_HEADER]: value },
        }),
      );

      expect(response.status, value).toBe(200);
      expect(response.headers.get("content-security-policy"), value).toMatch(/script-src 'self' 'nonce-[^']+' 'strict-dynamic'/);
      expect(response.headers.get(`${FORWARDED}${MIDDLEWARE_SUBREQUEST_HEADER}`), value).toBeNull();
      expect(forwardedNames(response), value).not.toContain(MIDDLEWARE_SUBREQUEST_HEADER);
      // The rest of the request still reaches the page.
      expect(response.headers.get(`${FORWARDED}cookie`), value).toContain("aw_session=tok");
    }
  });

  it("does not reach the hosted chat page either", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json({ error: "not_found" }, { status: 404 })),
    );

    const response = await proxy(
      new NextRequest("https://app.example.com/c/cafe-batumi", {
        headers: { [MIDDLEWARE_SUBREQUEST_HEADER]: "src/proxy:src/proxy:src/proxy:src/proxy:src/proxy" },
      }),
    );

    expect(response.headers.get("content-security-policy")).toContain("form-action 'none'");
    expect(response.headers.get(`${FORWARDED}${MIDDLEWARE_SUBREQUEST_HEADER}`)).toBeNull();
    expect(forwardedNames(response)).not.toContain(MIDDLEWARE_SUBREQUEST_HEADER);
  });
});

interface LockedPackage {
  version: string;
}

function lockedPackages(): Record<string, LockedPackage> {
  const lock = JSON.parse(readFileSync(path.resolve(__dirname, "../package-lock.json"), "utf8")) as {
    packages: Record<string, LockedPackage>;
  };
  return lock.packages;
}

/** Negative, zero or positive as `version` is older than, equal to or newer than `floor`. */
function compareVersions(version: string, floor: string): number {
  const parts = (text: string) => text.split("-")[0]!.split(".").map(Number);
  const [left, right] = [parts(version), parts(floor)];
  for (let index = 0; index < 3; index += 1) {
    const difference = (left[index] ?? 0) - (right[index] ?? 0);
    if (difference !== 0) {
      return difference;
    }
  }
  return 0;
}

describe("the installed framework", () => {
  // Next.js 16.0.7 and React 19.2.1 fixed CVE-2025-55182 (React2Shell);
  // the 15.2.3 line already fixed CVE-2025-29927.
  const FLOORS: Record<string, string> = {
    "node_modules/next": "16.0.7",
    "node_modules/react": "19.2.1",
    "node_modules/react-dom": "19.2.1",
  };

  it("is past the fixes of both advisories", () => {
    const packages = lockedPackages();
    for (const [name, floor] of Object.entries(FLOORS)) {
      const version = packages[name]?.version ?? "0.0.0";
      expect(compareVersions(version, floor), `${name} ${version}`).toBeGreaterThanOrEqual(0);
    }
    // A separately installed React Server Components package must be fixed too.
    for (const [name, locked] of Object.entries(packages)) {
      if (/node_modules\/react-server-dom-[a-z]+$/.test(name)) {
        expect(compareVersions(locked.version, "19.2.1"), `${name} ${locked.version}`).toBeGreaterThanOrEqual(0);
      }
    }
  });

  it("compares versions part by part", () => {
    expect(compareVersions("16.4.3", "16.0.7")).toBeGreaterThan(0);
    expect(compareVersions("16.0.6", "16.0.7")).toBeLessThan(0);
    expect(compareVersions("19.2.1", "19.2.1")).toBe(0);
    expect(compareVersions("19.10.0-rc.1", "19.2.1")).toBeGreaterThan(0);
  });
});

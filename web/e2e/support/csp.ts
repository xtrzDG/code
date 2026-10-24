/**
 * The Content Security Policy as a browser enforces it: every violation a
 * page reports (`securitypolicyviolation`: a refused style attribute, a
 * script sink without a Trusted Type, a script from elsewhere), from the
 * first script on, and the policy a response carries. The suite runs on a
 * production build (`next start`), which enforces the strict policy:
 * nonce'd styles only, Trusted Types (server/contentSecurityPolicy.ts).
 */

import type { Page } from "@playwright/test";

import { expect } from "./fixtures";

const watched = new WeakSet<Page>();

/** Starts collecting the page's violations (once per page; later calls do nothing). */
export async function watchPolicyViolations(page: Page): Promise<void> {
  if (watched.has(page)) {
    return;
  }
  watched.add(page);
  await page.addInitScript(() => {
    const violations: string[] = [];
    (window as unknown as { __cspViolations: string[] }).__cspViolations = violations;
    document.addEventListener("securitypolicyviolation", (event) => {
      const target = event.target instanceof Element ? event.target.outerHTML.slice(0, 160) : "";
      violations.push(`${event.effectiveDirective} ${event.blockedURI} ${target}`.trim());
    });
  });
}

/** The violations the page has reported since it loaded. */
export async function policyViolations(page: Page): Promise<string[]> {
  return page.evaluate(() => (window as unknown as { __cspViolations?: string[] }).__cspViolations ?? []);
}

/** The strict policy of a production build, as a response carries it. */
export function expectStrictPolicy(policy: string, where: string): void {
  expect(policy, where).toMatch(/script-src 'self' 'nonce-[A-Za-z0-9+/=]+' 'strict-dynamic'/);
  expect(policy, where).toMatch(/style-src 'self' 'nonce-[A-Za-z0-9+/=]+'(;|$)/);
  expect(policy, where).not.toContain("'unsafe-inline'");
  expect(policy, where).not.toContain("'unsafe-eval'");
  expect(policy, where).toContain("require-trusted-types-for 'script'");
  expect(policy, where).toContain("report-uri /api/csp-report");
  expect(policy, where).toContain("report-to csp");
}

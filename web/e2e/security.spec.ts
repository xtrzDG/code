/**
 * The cabinet's security headers: a Content Security Policy with a fresh
 * nonce on every page and no page breaking it, the isolation headers, the
 * BFF's body limit, and the bot check of the sign-in page (Cloudflare
 * Turnstile, faked here: the API asks for it, the page shows it).
 */

import type { Page } from "@playwright/test";

import { BUSINESS_PAGES, setupPath } from "../src/lib/navigation";

import { uniqueEmail } from "./support/api";
import { expect, test } from "./support/fixtures";
import { waitForNetworkQuiet } from "./support/network";
import { en } from "./support/messages";

const TURNSTILE_SCRIPT = "https://challenges.cloudflare.com/turnstile/v0/api.js*";
/** Stands in for Cloudflare's script: a button that "passes" the check. */
const FAKE_TURNSTILE = `
window.turnstile = {
  render(container, options) {
    window.__turnstile = { sitekey: options.sitekey, action: options.action };
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "I am human";
    button.addEventListener("click", () => options.callback("e2e-turnstile-token"));
    container.append(button);
    return "widget-1";
  },
  reset() {},
  remove() {},
};
`;

/** Collects every CSP violation the page reports, from the first script on. */
async function watchPolicyViolations(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const violations: string[] = [];
    (window as unknown as { __cspViolations: string[] }).__cspViolations = violations;
    document.addEventListener("securitypolicyviolation", (event) => {
      violations.push(`${event.violatedDirective} ${event.blockedURI}`);
    });
  });
}

async function policyViolations(page: Page): Promise<string[]> {
  return page.evaluate(() => (window as unknown as { __cspViolations: string[] }).__cspViolations);
}

async function openAndCheck(page: Page, path: string): Promise<string> {
  const response = await page.goto(path);
  expect(response, path).not.toBeNull();
  await waitForNetworkQuiet(page);
  expect(await policyViolations(page), `${path} broke the Content Security Policy`).toEqual([]);
  const policy = response?.headers()["content-security-policy"] ?? "";
  expect(policy, path).toMatch(/script-src 'self' 'nonce-[A-Za-z0-9+/=]+' 'strict-dynamic'/);
  expect(policy, path).toContain("frame-ancestors 'none'");
  return policy;
}

test.describe("Content Security Policy", () => {
  test("no public page breaks it, and every view has a new nonce", async ({ page }) => {
    await watchPolicyViolations(page);

    const first = await openAndCheck(page, "/");
    const second = await openAndCheck(page, "/");
    await openAndCheck(page, "/login");

    expect(first).not.toEqual(second);
    // Next.js puts the nonce on its own scripts.
    const nonce = /'nonce-([^']+)'/.exec(second)?.[1];
    expect(nonce).toBeTruthy();
  });

  test.describe("with motion", () => {
    test.use({ contextOptions: { reducedMotion: "no-preference" } });

    test("the landing's 3D hero does not break it", async ({ page }) => {
      await watchPolicyViolations(page);

      await openAndCheck(page, "/");
      // The scene has loaded its chunk and drawn once the hero says so.
      const hero = page.getByRole("img", { name: en.landing.hero.sceneLabel });
      await expect(hero).toHaveAttribute("data-scene", "3d", { timeout: 30_000 });
      await expect(hero.locator("canvas")).toHaveCount(1);
      expect(await policyViolations(page)).toEqual([]);
    });
  });

  test("no page of a business breaks it", async ({ page, owner }) => {
    test.setTimeout(120_000);
    await watchPolicyViolations(page);

    await openAndCheck(page, "/businesses");
    for (const businessPage of BUSINESS_PAGES) {
      await test.step(businessPage, async () => {
        await openAndCheck(page, `/b/${owner.businessId}/${businessPage}`);
        await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
      });
    }
  });

  test("the setup invitation and the setup flow do not break it", async ({ page, newOwner }) => {
    await watchPolicyViolations(page);

    for (const path of [`/b/${newOwner.businessId}/overview`, setupPath(newOwner.businessId)]) {
      await test.step(path, async () => {
        await openAndCheck(page, path);
        await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
      });
    }
  });

  test("pages send the isolation headers", async ({ page }) => {
    const response = await page.goto("/login");
    const headers = response?.headers() ?? {};

    expect(headers["cross-origin-opener-policy"]).toBe("same-origin");
    expect(headers["cross-origin-resource-policy"]).toBe("same-origin");
    expect(headers["x-frame-options"]).toBe("DENY");
    expect(headers["x-content-type-options"]).toBe("nosniff");
    // A production build always sends HSTS; browsers honour it only over HTTPS.
    expect(headers["strict-transport-security"]).toContain("max-age=63072000");
  });
});

test.describe("the BFF", () => {
  test("refuses a body over its limit with 413", async ({ page, owner }) => {
    const response = await page.request.patch(`/api/backend/v1/businesses/${owner.businessId}`, {
      data: { name: "x".repeat(300 * 1024) },
    });

    expect(response.status()).toBe(413);
    expect((await response.json()).error).toBe("payload_too_large");
  });
});

test.describe("the sign-in page", () => {
  test("shows the bot check only when the API asks for it, then sends the code", async ({ page, consoleErrors }) => {
    // The browser reports the refused first request itself.
    consoleErrors.allow(/Failed to load resource: the server responded with a status of 403/);
    await watchPolicyViolations(page);
    await page.route(TURNSTILE_SCRIPT, (route) =>
      route.fulfill({ contentType: "text/javascript", body: FAKE_TURNSTILE }),
    );
    const startBodies: Record<string, unknown>[] = [];
    await page.route("**/api/auth/start", async (route) => {
      startBodies.push(route.request().postDataJSON() as Record<string, unknown>);
      if (startBodies.length === 1) {
        await route.fulfill({
          status: 403,
          json: {
            error: "access_denied",
            message: "Confirm that you are not a robot, then ask for the code again.",
            reasons: [{ code: "challenge_required", message: "Confirm.", details: ["1x00000000000000000000AA"] }],
          },
        });
        return;
      }
      await route.continue();
    });

    await page.goto("/login");
    await expect(page.getByRole("group", { name: en.auth.botCheck.title })).toHaveCount(0);
    await page.getByRole("group", { name: en.auth.methodLabel }).getByText(en.auth.methodEmail, { exact: true }).click();
    await page.getByRole("textbox", { name: en.auth.email, exact: true }).fill(uniqueEmail());
    await page.getByRole("button", { name: en.auth.sendCode }).click();

    const check = page.getByRole("group", { name: en.auth.botCheck.title });
    await expect(check).toBeVisible();
    await expect(check.getByText(en.auth.botCheck.hint)).toBeVisible();
    expect(await page.evaluate(() => (window as unknown as { __turnstile: unknown }).__turnstile)).toEqual({
      sitekey: "1x00000000000000000000AA",
      action: "login",
    });
    await check.getByRole("button", { name: "I am human" }).click();

    await expect(page.getByRole("heading", { name: en.auth.codeTitle })).toBeVisible();
    expect(startBodies).toHaveLength(2);
    expect(startBodies[0]).not.toHaveProperty("turnstile_token");
    expect(startBodies[1]).toMatchObject({ turnstile_token: "e2e-turnstile-token" });
    await expect(check).toHaveCount(0);
    expect(await policyViolations(page)).toEqual([]);
  });
});

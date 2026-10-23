/**
 * The cabinet's security headers: a Content Security Policy with a fresh
 * nonce on every page, no inline style and Trusted Types, and no page
 * breaking it (the route tour checks every other route, support/tour.ts);
 * its violation reports; the isolation headers, the BFF's body limit, and
 * the bot check of the sign-in page (Cloudflare Turnstile, faked here: the
 * API asks for it, the page shows it).
 */

import type { Page } from "@playwright/test";

import { BUSINESS_PAGES, setupPath } from "../src/lib/navigation";

import { uniqueEmail } from "./support/api";
import { expectStrictPolicy, policyViolations, watchPolicyViolations } from "./support/csp";
import { expect, test } from "./support/fixtures";
import { emulateCapableDesktop } from "./support/heroScene";
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

async function openAndCheck(page: Page, path: string): Promise<string> {
  const response = await page.goto(path);
  expect(response, path).not.toBeNull();
  await waitForNetworkQuiet(page);
  expect(await policyViolations(page), `${path} broke the Content Security Policy`).toEqual([]);
  const policy = response?.headers()["content-security-policy"] ?? "";
  expectStrictPolicy(policy, path);
  expect(policy, path).toContain("frame-ancestors 'none'");
  expect(response?.headers()["reporting-endpoints"], path).toBe('csp="/api/csp-report"');
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
      // The scene loads only on a device meant for it, whatever the runner has.
      await emulateCapableDesktop(page);
      await watchPolicyViolations(page);

      await openAndCheck(page, "/");
      // The scene has loaded its chunk and drawn once the hero says so.
      const hero = page.getByRole("img", { name: en.landing.hero.sceneLabel });
      await expect(hero).toHaveAttribute("data-scene", "3d", { timeout: 30_000 });
      await expect(hero.locator("canvas")).toHaveCount(1);
      expect(await policyViolations(page)).toEqual([]);
    });
  });

  test("a page that is not found does not break it", async ({ page, owner, consoleErrors }) => {
    // Next.js answers notFound() with its error shell: the policy is installed there too.
    consoleErrors.allow(/status of 404 \(Not Found\)/);
    await watchPolicyViolations(page);

    await openAndCheck(page, "/c/no-chat-e2e-0000");
    await expect(page.getByRole("heading", { name: "There is no chat at this address. Check the link." })).toBeVisible();
    await openAndCheck(page, `/b/${owner.businessId}/assistant/profile/no-such-section`);
    await expect(page.getByText(en.errors.notFoundTitle)).toBeVisible();
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

test.describe("the policy in the browser", () => {
  test("refuses a style attribute and markup a script makes up, and reports both", async ({ page, consoleErrors }) => {
    // Older Chrome says "Refused to apply inline style", newer Chrome
    // "Applying inline style violates"; both mean the attribute was refused.
    consoleErrors.allow(/Refused to apply inline style|Applying inline style violates|requires 'TrustedHTML' assignment/);
    await watchPolicyViolations(page);
    await openAndCheck(page, "/login");

    const outcome = await page.evaluate(() => {
      const probe = document.createElement("p");
      document.body.append(probe);
      // A property whose computed value never depends on another one (newer
      // Chrome computes outline-width as 3px even with no outline style).
      probe.setAttribute("style", "margin-left: 37px");
      const styled = getComputedStyle(probe).marginLeft;
      let markup = "set";
      try {
        probe.innerHTML = '<img src="x" alt="">';
      } catch (error) {
        markup = error instanceof TypeError ? "refused" : "other";
      }
      probe.textContent = "plain text still works";
      return { styled, markup, text: probe.textContent };
    });

    expect(outcome).toEqual({ styled: "0px", markup: "refused", text: "plain text still works" });
    await expect.poll(async () => (await policyViolations(page)).map((line) => line.split(" ")[0])).toEqual(
      expect.arrayContaining(["style-src-attr", "require-trusted-types-for"]),
    );
  });
});

test.describe("violation reports", () => {
  const REPORT = {
    "csp-report": {
      "document-uri": "http://localhost/b/business_1/overview?view=all",
      "effective-directive": "style-src-attr",
      "blocked-uri": "inline",
    },
  };

  test("are accepted from browsers and anything else is refused", async ({ page }) => {
    const send = (data: string, contentType = "application/csp-report") =>
      page.request.post("/api/csp-report", { data, headers: { "content-type": contentType } });

    expect((await send(JSON.stringify(REPORT))).status()).toBe(204);
    const batch = [{ type: "csp-violation", url: "http://localhost/help", body: { effectiveDirective: "img-src", blockedURL: "inline" } }];
    expect((await send(JSON.stringify(batch), "application/reports+json")).status()).toBe(204);
    expect((await send(JSON.stringify(REPORT), "text/plain")).status()).toBe(415);
    expect((await send("not json")).status()).toBe(400);
    expect((await send("x".repeat(20 * 1024))).status()).toBe(413);
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

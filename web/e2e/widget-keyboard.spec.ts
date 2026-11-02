/**
 * The website chat widget on a host site, for people who use the keyboard,
 * a screen reader or reduced motion (WCAG 2.1.1, 2.1.2, 2.4.3, 3.1.2,
 * 2.3.3), when the chat cannot answer (the business's phone instead), and
 * embedded through its loader with an integrity hash (a changed loader
 * never runs). The widget script is the one the real API serves; its API
 * is faked (support/widget-site.ts).
 */

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";

import type { Page } from "@playwright/test";

import { REPOSITORY_ROOT } from "./support/env";
import { expect, test } from "./support/fixtures";
import { API, BUSINESS, FakeWidgetApi, SITE, ask, chat, loadWidgetSource, serveSite } from "./support/widget-site";

const WRAPPER = "[data-assistant-workshop-chat] .aw";
const LOADER_SOURCE = readFileSync(path.join(REPOSITORY_ROOT, "app/utilities/channels/widget_loader.js"));
const PHONE = "+390612345678";

test.beforeAll(async () => {
  await loadWidgetSource();
});

/** Whether the keyboard focus is inside the widget (its shadow root keeps the element). */
function focusIsInWidget(page: Page): Promise<boolean> {
  return page.evaluate(() => document.activeElement?.hasAttribute("data-assistant-workshop-chat") ?? false);
}

test("the keyboard alone opens the chat, writes, closes it with Escape and moves on to the host page", async ({ page }) => {
  await serveSite(page.context(), new FakeWidgetApi());
  await page.goto(`${SITE}/`);
  const launcher = page.getByRole("button", { name: "Open chat" });
  await expect(launcher).toBeVisible();

  // The host page's own link first, then the launcher (it comes after it).
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Next page" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(launcher).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(chat(page)).toBeVisible();
  await expect(page.getByRole("textbox")).toBeFocused();
  await page.keyboard.type("Is the terrace open?");
  await page.keyboard.press("Enter");
  await expect(chat(page).getByText("Answer to Is the terrace open?")).toBeVisible();

  // Escape closes the chat and gives the focus back to the launcher.
  await page.keyboard.press("Escape");
  await expect(chat(page)).toBeHidden();
  await expect(page.getByRole("button", { name: "Open chat" })).toBeFocused();

  // Open again: Tab walks through the chat and out of it (no keyboard trap).
  await page.keyboard.press("Enter");
  await expect(page.getByRole("textbox")).toBeFocused();
  let presses = 0;
  while ((await focusIsInWidget(page)) && presses < 40) {
    await page.keyboard.press("Tab");
    presses += 1;
  }
  expect(await focusIsInWidget(page), "Tab leaves the open chat").toBe(false);
  expect(presses).toBeGreaterThan(1);
});

test("the widget says its language and leaves the host page's own", async ({ page }) => {
  const api = new FakeWidgetApi();
  api.configExtras = {
    languages: [
      { tag: "en", direction: "ltr", native_name: "English" },
      { tag: "it", direction: "ltr", native_name: "Italiano" },
    ],
  };
  await serveSite(page.context(), api, { attributes: { "data-language": "it" } });
  await page.goto(`${SITE}/`);

  await expect(page.getByRole("button", { name: "Apri la chat" })).toBeVisible();
  await expect(page.locator(WRAPPER)).toHaveAttribute("lang", "it");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
});

test("with reduced motion the launcher and the typing dots do not move", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  const api = new FakeWidgetApi();
  api.holdAnswers = true;
  await serveSite(page.context(), api);
  await page.goto(`${SITE}/`);

  const launcher = page.getByRole("button", { name: "Open chat" });
  await expect(launcher).toBeVisible();
  expect(await launcher.evaluate((element) => getComputedStyle(element).transitionDuration)).toBe("0s");
  await launcher.click();
  await ask(page, "Is the terrace open?");
  const dot = page.locator("[data-assistant-workshop-chat] .aw-typing span").first();
  await expect(dot).toBeVisible();
  expect(await dot.evaluate((element) => getComputedStyle(element).animationName)).toBe("none");
});

test("when the chat cannot answer, the business's phone is offered under the message", async ({ page, consoleErrors }) => {
  // The browser itself logs the refused request.
  consoleErrors.allow(/status of 503/);
  const api = new FakeWidgetApi();
  api.configExtras = { business_phone_number: PHONE };
  await serveSite(page.context(), api);
  // The API is down for messages: every new one is answered 503.
  await page.context().route(`${API}/v1/widget/*/messages`, (route) =>
    route.request().method() === "POST"
      ? route.fulfill({ status: 503, headers: { "access-control-allow-origin": "*" }, json: { error: "unavailable" } })
      : route.fallback(),
  );
  await page.goto(`${SITE}/`);

  await page.getByRole("button", { name: "Open chat" }).click();
  await ask(page, "Is the terrace open?");
  await expect(chat(page).getByText("Message not sent.")).toBeVisible();
  const call = chat(page).getByRole("link", { name: `Call ${PHONE}` });
  await expect(call).toBeVisible();
  await expect(call).toHaveAttribute("href", `tel:${PHONE}`);
  await expect(chat(page).getByText("Other ways to reach us:")).toBeVisible();
});

for (const isTampered of [false, true]) {
  test(`the embed code's loader runs only as its integrity hash says (${isTampered ? "changed" : "as published"})`, async ({
    page,
    consoleErrors,
  }) => {
    const version = createHash("sha256").update(LOADER_SOURCE).digest("hex").slice(0, 16);
    const integrity = `sha384-${createHash("sha384").update(LOADER_SOURCE).digest("base64")}`;
    const served = isTampered ? Buffer.concat([LOADER_SOURCE, Buffer.from("\n// changed on the way\n")]) : LOADER_SOURCE;
    await serveSite(page.context(), new FakeWidgetApi());
    // Registered last, so it answers before serveSite's own page.
    await page.context().route(`${SITE}/**`, (route) =>
      route.fulfill({
        contentType: "text/html",
        body:
          `<!doctype html><html lang="en"><head><title>Shop</title></head><body><h1>Shop</h1>` +
          `<script src="${API}/widget/v/${version}.js" integrity="${integrity}" crossorigin="anonymous" data-tenant="${BUSINESS}" async></script>` +
          `</body></html>`,
      }),
    );
    await page.context().route(`${API}/widget/v/*.js`, (route) =>
      route.fulfill({
        headers: { "access-control-allow-origin": "*", "content-type": "text/javascript; charset=utf-8" },
        body: served,
      }),
    );
    if (isTampered) {
      consoleErrors.allow(/integrity/i);
    }

    await page.goto(`${SITE}/`);

    if (isTampered) {
      await page.waitForLoadState("networkidle");
      await expect(page.locator("[data-assistant-workshop-chat]")).toHaveCount(0);
    } else {
      await expect(page.getByRole("button", { name: "Open chat" })).toBeVisible();
    }
  });
}

/**
 * The platform admin's niche template editor: a SUPER admin rewords the
 * first question of the veterinary template in Russian, sees it in the
 * preview, saves the draft and publishes it; a new owner who opens "Create
 * an AI assistant" in Russian reads the new question; going back to the
 * code template restores the code's wording for the next owner. The page
 * passes the accessibility audit; owners get "Page not found".
 *
 * Veterinary clinics: no other spec walks that niche, so the published
 * wording never meets another spec's tunnel (the suite's API is shared).
 */

import AxeBuilder from "@axe-core/playwright";
import type { APIRequestContext, Browser, BrowserContext, Page } from "@playwright/test";

import { signInAsPlatformAdmin } from "./support/admin";
import { signInByEmail, uniqueEmail } from "./support/api";
import { NICHES_ADMIN_EMAIL, WEB_URL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";
import { trackRequests, waitForNetworkQuiet } from "./support/network";

const texts = en.adminNiches;
const CODE_LABEL = "Каких животных вы лечите?";
const NEW_LABEL = "Каких питомцев вы принимаете?";

async function openAdmin(browser: Browser, request: APIRequestContext): Promise<{ context: BrowserContext; admin: Page }> {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  await signInContext(context, await signInAsPlatformAdmin(request, NICHES_ADMIN_EMAIL));
  const admin = await context.newPage();
  trackRequests(admin);
  return { context, admin };
}

/** A new owner's first screen of "Create an AI assistant", in Russian, with the veterinary niche chosen. */
async function tunnelQuestion(browser: Browser, request: APIRequestContext, label: string): Promise<void> {
  const context = await browser.newContext({ reducedMotion: "reduce" });
  await signInContext(context, await signInByEmail(request, uniqueEmail()));
  await context.addCookies([{ name: "aw_locale", value: "ru", url: WEB_URL }]);
  const owner = await context.newPage();
  await owner.goto("/create");
  await owner.locator("label").filter({ hasText: /^Ветклиники/ }).click();
  await expect(owner.getByRole("group", { name: label })).toBeVisible();
  await context.close();
}

test("an admin rewords a question in Russian, new owners read it, and the code template comes back", async ({
  browser,
  request,
}) => {
  const { context, admin } = await openAdmin(browser, request);

  await admin.goto("/admin");
  const navigation = admin.getByRole("navigation", { name: en.nav.mainNavigation });
  await navigation.getByRole("link", { name: texts.nav }).click();
  await expect(admin).toHaveURL(/\/admin\/niches$/);
  await expect(admin.getByRole("heading", { level: 1, name: texts.title })).toBeVisible();
  await admin.getByRole("link", { name: texts.edit.replace("{niche}", "Veterinary clinics and grooming") }).click();
  await expect(admin).toHaveURL(/\/admin\/niches\/veterinary\?language=en$/);
  await expect(admin.getByRole("heading", { level: 1, name: "Veterinary clinics and grooming" })).toBeVisible();

  await admin.getByRole("tab", { name: "Русский" }).click();
  await expect(admin).toHaveURL(/language=ru$/);
  // Every part of the template is folded to its title until opened.
  const questionTitle = `${texts.editor.question.replace("{position}", "1")} · ${CODE_LABEL}`;
  await admin.locator("summary", { hasText: questionTitle }).click();
  const question = admin.getByRole("group", { name: questionTitle });
  await expect(question.getByText(texts.editor.code.replace("{text}", CODE_LABEL))).toBeVisible();
  await question.getByLabel(texts.editor.fields.label).fill(`<b>${NEW_LABEL}</b>`);
  await expect(question.getByText(texts.editor.errors.html)).toBeVisible();
  await expect(admin.getByRole("button", { name: texts.editor.saveDraft })).toBeDisabled();
  await question.getByLabel(texts.editor.fields.label).fill(NEW_LABEL);
  const preview = admin.getByRole("region", { name: en.adminNiches.preview.title });
  await expect(preview.getByText(NEW_LABEL)).toBeVisible();
  await admin.getByRole("button", { name: texts.editor.saveDraft }).click();
  await expect(admin.getByText(texts.editor.draftSaved)).toBeVisible();
  await expect(admin.getByText(texts.editor.draftWaiting)).toBeVisible();

  await admin.getByRole("button", { name: texts.editor.publish, exact: true }).click();
  const publish = admin.getByRole("dialog", { name: texts.editor.publishTitle.replace("{niche}", "Veterinary clinics and grooming") });
  await publish.getByRole("button", { name: texts.editor.publish }).click();
  await expect(admin.getByText(texts.editor.published.replace("{version}", "1"))).toBeVisible();
  const versions = admin.getByRole("list", { name: texts.history.title });
  await expect(versions.getByText(`${texts.version.replace("{version}", "1")} · ${texts.history.kinds.publish}`)).toBeVisible();

  await tunnelQuestion(browser, request, NEW_LABEL);

  await versions.getByRole("button", { name: texts.history.reset }).click();
  const reset = admin.getByRole("dialog", { name: texts.history.resetTitle.replace("{niche}", "Veterinary clinics and grooming") });
  await reset.getByRole("button", { name: texts.history.reset }).click();
  await expect(admin.getByText(texts.history.restored.replace("{version}", "2"))).toBeVisible();
  await expect(versions.getByText(`${texts.version.replace("{version}", "2")} · ${texts.history.kinds.reset}`)).toBeVisible();

  await tunnelQuestion(browser, request, CODE_LABEL);

  await waitForNetworkQuiet(admin);
  const results = await new AxeBuilder({ page: admin }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  const serious = results.violations.filter((violation) => violation.impact === "serious" || violation.impact === "critical");
  expect(serious.map((violation) => violation.id)).toEqual([]);
  await context.close();
});

test("the niche templates are not there for owners", async ({ page, account, consoleErrors }) => {
  expect(account.email).toBeTruthy();
  consoleErrors.allow(/status of 404 \(Not Found\) \(http:\/\/localhost:\d+\/(admin\/niches|favicon\.ico)\)/);
  const response = await page.goto("/admin/niches");

  expect(response?.status()).toBe(404);
  await expect(page.getByText(en.errors.notFoundTitle)).toBeVisible();
});

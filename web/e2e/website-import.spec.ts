/**
 * Knowledge -> Import -> "From your website": the API refuses a private
 * address (the SSRF guard, against the real API); a queued import shows its
 * progress, finishes and opens its drafts in the shared review; a failed one
 * is explained. The import itself is served by the test (no website is read
 * and no worker runs in the suite); the rest of the cabinet is the real one.
 */

import AxeBuilder from "@axe-core/playwright";
import type { Page, Route } from "@playwright/test";

import type { Schema } from "../src/api/types";
import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";
import { waitForNetworkQuiet } from "./support/network";

type WebsiteImport = Schema<"WebsiteImportView">;

const website = en.knowledge.website;

function importOf(businessId: string, changes: Partial<WebsiteImport>): WebsiteImport {
  return {
    id: "website_import_e2e",
    business_id: businessId,
    status: "queued",
    url: "https://cafe.example/",
    pages_planned: 0,
    pages_read: 0,
    pages_skipped: 0,
    items_found: 0,
    problem: null,
    problem_detail: null,
    started_at: Date.now() * 1000,
    finished_at: null,
    result: null,
    ...changes,
  };
}

function draft(id: string, title: string, sourcePage: string): Schema<"ImportedMenuItemView"> {
  return {
    item: { id, kind: "faq", title, body: "Every day from 9:00 to 22:00.", tags: [] },
    confidence: 0.9,
    is_currency_mismatch: false,
    source_page_url: sourcePage,
  };
}

/** Serves the business's current import from `current()` and records the starts. */
async function serveImport(page: Page, current: () => WebsiteImport | null, started: string[]): Promise<void> {
  await page.route("**/knowledge/import-website/current", (route: Route) => route.fulfill({ json: { current: current() } }));
  await page.route("**/knowledge/import-website", (route: Route) => {
    const body = route.request().postDataJSON() as { url: string };
    started.push(body.url);
    return route.fulfill({ status: 202, json: current() });
  });
}

async function seriousViolations(page: Page): Promise<string[]> {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  return results.violations
    .filter((violation) => violation.impact === "serious" || violation.impact === "critical")
    .map((violation) => `${violation.id}: ${violation.nodes.map((node) => node.target.join(" ")).join(" | ")}`);
}

test("a private address is refused by the API and explained", async ({ page, owner, consoleErrors }) => {
  consoleErrors.allow(/status of 422/);
  await page.goto(`/b/${owner.businessId}/assistant/knowledge/import`);
  await page.getByRole("tab", { name: website.tabWebsite }).click();
  await expect(page).toHaveURL(/\?source=website$/);
  await expect(page.getByRole("tab", { name: website.tabWebsite })).toHaveAttribute("aria-selected", "true");

  const address = page.getByLabel(website.address);
  await page.getByRole("button", { name: website.start }).click();
  await expect(page.getByText(website.errors.required)).toBeVisible();

  await address.fill("http://127.0.0.1/admin");
  await page.getByRole("button", { name: website.start }).click();
  await expect(page.getByText(website.errors.notPublic)).toBeVisible();
  await expect(address).toHaveAttribute("aria-invalid", "true");
  await waitForNetworkQuiet(page);
  expect(await seriousViolations(page)).toEqual([]);

  // The menu tab is still one click away, and the address forgets the source.
  await page.getByRole("tab", { name: website.tabMenu }).click();
  await expect(page).not.toHaveURL(/source=/);
  await expect(page.getByRole("heading", { name: en.knowledge.import.title })).toBeVisible();
});

test("a queued import shows its progress and opens its drafts in the review", async ({ page, owner }) => {
  let current: WebsiteImport | null = null;
  const started: string[] = [];
  await serveImport(page, () => current, started);
  await page.goto(`/b/${owner.businessId}/assistant/knowledge/import?source=website`);
  await expect(page.getByRole("heading", { name: website.title })).toBeVisible();

  current = importOf(owner.businessId, { status: "queued" });
  await page.getByLabel(website.address).fill("cafe.example");
  await page.getByRole("button", { name: website.start }).click();
  await expect.poll(() => started).toEqual(["https://cafe.example/"]);
  const progress = page.getByRole("progressbar", { name: website.progressLabel });
  await expect(progress).toBeVisible();
  await expect(page.getByText(website.queued)).toBeVisible();
  await waitForNetworkQuiet(page);
  expect(await seriousViolations(page)).toEqual([]);

  // The worker reads the site: the page polls while it runs.
  current = importOf(owner.businessId, { status: "reading", pages_planned: 5, pages_read: 2, items_found: 3 });
  await expect(page.getByText("Reading page 3 of 5")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("3 items found so far")).toBeVisible();
  await expect(progress).toHaveAttribute("aria-valuenow", "46");

  current = importOf(owner.businessId, {
    status: "done",
    pages_planned: 5,
    pages_read: 5,
    items_found: 2,
    finished_at: Date.now() * 1000,
    result: {
      business_id: owner.businessId,
      batch_id: "menu_import_batch_e2e",
      skipped_line_count: 0,
      items: [
        draft("knowledge_item_hours", "Opening hours", "https://cafe.example/contact"),
        draft("knowledge_item_parking", "Is there parking?", "https://cafe.example/faq?lang=en"),
      ],
    },
  });
  await expect(page.getByText("Found 2 items on your website")).toBeVisible({ timeout: 10_000 });
  await page.getByRole("button", { name: website.review }).click();

  await expect(page.getByText("Opening hours")).toBeVisible();
  await expect(page.getByRole("link", { name: "From /faq?lang=en" })).toHaveAttribute("href", "https://cafe.example/faq?lang=en");
  await expect(page.getByRole("link", { name: "From /contact" })).toHaveAttribute("rel", "noopener noreferrer");
});

test("an import that could not read the site says why and offers the address again", async ({ page, owner }) => {
  const failed = importOf(owner.businessId, {
    status: "failed",
    url: "https://cafe.example/menu",
    problem: "website_link_unreachable",
    problem_detail: "http_status:404",
    finished_at: Date.now() * 1000,
  });
  const started: string[] = [];
  await serveImport(page, () => failed, started);
  await page.goto(`/b/${owner.businessId}/assistant/knowledge/import?source=website`);

  await expect(page.getByText(website.errors.failedTitle)).toBeVisible();
  await expect(page.getByText("The website answered with error 404. Check the address.")).toBeVisible();
  await expect(page.getByLabel(website.address)).toHaveValue("https://cafe.example/menu");
  expect(started).toEqual([]);
});

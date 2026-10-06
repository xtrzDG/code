import type { Schema } from "../src/api/types";
import { rateSourceKey } from "../src/lib/publicSite/prices";
import { API_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { en, ka, ru } from "./support/messages";

/**
 * The public site around the cabinet: every page in its language under its
 * own address (/en, /ru/for/hotel, /ka/privacy) with hreflang alternates,
 * structured data and a sitemap; the footer's links all open; the legal
 * texts say they are drafts; prices never show a raw conversion.
 */
const DICTIONARIES = { en, ru, ka } as const;

test.describe("the public site", () => {
  test("sends the root and a legal page without a language to the reader's", async ({ page }) => {
    await page.goto("/?country=GE");
    await expect(page).toHaveURL(/\/en\?country=GE$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");

    await page.goto("/privacy");
    await expect(page).toHaveURL(/\/en\/privacy$/);
  });

  for (const locale of ["en", "ru", "ka"] as const) {
    test(`renders a niche page in ${locale} with its alternates and structured data`, async ({ page }) => {
      const t = DICTIONARIES[locale];
      await page.goto(`/${locale}/for/restaurant`);

      await expect(page.locator("html")).toHaveAttribute("lang", locale);
      await expect(page.getByText(t.nichePage.eyebrow)).toBeVisible();
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", new RegExp(`/${locale}/for/restaurant$`));
      for (const alternate of ["ka", "ru", "en", "x-default"]) {
        await expect(page.locator(`link[rel="alternate"][hreflang="${alternate}"]`)).toHaveCount(1);
      }
      const structured = await page.locator('script[type="application/ld+json"]').first().textContent();
      expect(JSON.parse(structured ?? "{}")).toMatchObject({ "@type": "Service", inLanguage: locale });
      // The calculator starts at this kind of business.
      await page.locator("#roi").scrollIntoViewIfNeeded();
      await expect(page.getByTestId("roi-calculator").getByLabel(t.roi.niche)).toHaveValue("restaurant");
    });
  }

  test("answers 404 for an unknown kind of business or language", async ({ request }) => {
    expect((await request.get("/en/for/spaceships")).status()).toBe(404);
    expect((await request.get("/fr")).status()).toBe(404);
  });

  test("links every footer page to a page that opens", async ({ page, request }) => {
    await page.goto("/en");
    const footer = page.getByTestId("site-footer");
    const hrefs = await footer.locator("a[href^='/']").evaluateAll((links) => links.map((link) => link.getAttribute("href") ?? ""));
    const pages = [...new Set(hrefs.map((href) => href.split("#")[0] ?? "").filter((href) => href !== "" && href !== "/login"))];
    expect(pages).toEqual(expect.arrayContaining(["/en/terms", "/en/privacy", "/en/dpa", "/en/security", "/en/contact", "/en/for/restaurant"]));
    for (const path of pages) {
      const response = await request.get(path);
      expect(response.status(), path).toBe(200);
    }
  });

  test("shows the legal texts with a draft banner while they are not final", async ({ page }) => {
    await page.goto("/ru/terms");
    await expect(page.getByTestId("legal-draft")).toContainText(ru.legalPages.draftTitle);
    await expect(page.getByTestId("legal-text").getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);

    await page.getByRole("link", { name: ru.legalPages.nav.dpa }).first().click();
    await expect(page).toHaveURL(/\/ru\/dpa$/);
    await expect(page.getByText(ru.legalPages.dpaLead)).toBeVisible();

    await page.goto("/en/contact");
    await expect(page.getByTestId("contact-details").getByRole("heading", { level: 1, name: en.legalPages.contactTitle })).toBeVisible();
    await expect(page.getByRole("link", { name: en.legalPages.securityReportLink })).toHaveAttribute("href", "/.well-known/security.txt");
  });

  test("links the documents from the sign-in card", async ({ page }) => {
    await page.goto("/login");
    const links = page.getByTestId("login-legal-links");
    await links.getByRole("link", { name: en.legalPages.nav.privacy }).click();
    await expect(page).toHaveURL(/\/en\/privacy$/);
  });

  test("lists the public pages in the sitemap and points robots to it", async ({ request }) => {
    const sitemap = await (await request.get("/sitemap.xml")).text();
    expect(sitemap).toContain("/ka/for/restaurant");
    expect(sitemap).toContain('hreflang="ru"');
    // Drafts are not offered to search engines.
    expect(sitemap).not.toContain("/en/terms");
    const robots = await (await request.get("/robots.txt")).text();
    expect(robots).toMatch(/Sitemap: http.*\/sitemap\.xml/);
    expect(robots).toContain("Disallow: /b/");
  });

  test("prices a country without a price book in euros first, the conversion rounded", async ({ page, request }) => {
    await page.goto("/en?country=US");
    const pricing = page.locator("#pricing");
    await pricing.scrollIntoViewIfNeeded();
    await expect(pricing.getByTestId("plan-price").first()).toHaveText(/^€\d+$/);
    await expect(pricing.getByTestId("plan-price-converted").first()).toContainText(/≈ \$\d+(?!\.)/);
    // No raw conversion anywhere: "$1,145.97"-style amounts never appear.
    expect(await pricing.innerText()).not.toMatch(/\$[\d,]+\.\d{2}/);
    // The note names the rate the API priced with: the ECB's once the
    // worker has read it (CI reaches the bank), else the planning rate.
    const response = await request.get(`${API_URL}/v1/catalog/plans?country_code=US&language=en`);
    const { exchange_rate: rate } = (await response.json()) as Schema<"PlanQuoteList">;
    expect(rate).toBeTruthy();
    await expect(pricing.getByTestId("pricing-notes")).toContainText(en.publicPricing.rateSources[rateSourceKey(rate!)]);
  });

  test("switches a public page to another language at its own address", async ({ page }) => {
    await page.goto("/en/for/hotel");
    await page.getByRole("combobox", { name: en.language.label }).selectOption("ka");
    await expect(page).toHaveURL(/\/ka\/for\/hotel$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "ka");
    await expect(page.getByText(ka.nichePage.eyebrow)).toBeVisible();
  });
});

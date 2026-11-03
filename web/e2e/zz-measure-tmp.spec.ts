// TEMPORARY measurement spec (deleted after use): the height of each card of
// the admin system and client pages at 390 px.
import { ensureOnAdminTeam, signInAsPlatformAdmin } from "./support/admin";
import { signInAsDemoOwner } from "./support/demo";
import { PLATFORM_ADMIN_EMAIL, TOUR_ADMIN_EMAIL, WEB_URL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { waitForNetworkQuiet } from "./support/network";

test.describe.configure({ timeout: 180_000 });
test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

test("measure", async ({ page, request }) => {
  const owner = await signInAsDemoOwner(request);
  await signInAsPlatformAdmin(request, PLATFORM_ADMIN_EMAIL);
  await ensureOnAdminTeam(request, TOUR_ADMIN_EMAIL);
  const token = await signInAsPlatformAdmin(request, TOUR_ADMIN_EMAIL);
  await signInContext(page.context(), token);
  const paths = (process.env.MEASURE_PATHS ?? "/admin/system,/admin/clients/{id}").split(",");
  for (const locale of (process.env.MEASURE_LOCALES ?? "it,en").split(",")) {
    await page.context().addCookies([
      { name: "aw_theme", value: "light", url: WEB_URL },
      { name: "aw_locale", value: locale, url: WEB_URL },
      { name: "aw_consent", value: "1.denied", url: WEB_URL },
    ]);
    for (const raw of paths) {
      const path = raw.replace("{id}", owner.businessId);
      await page.goto(path);
      await expect(page.locator("h1").first()).toBeAttached();
      await waitForNetworkQuiet(page, { quietMs: 800 });
      await expect(page.locator('[aria-busy="true"]:visible')).toHaveCount(0);
      const report = await page.evaluate(() => {
        const lines: string[] = [`scrollHeight ${document.documentElement.scrollHeight}`];
        const walk = (element: Element, depth: number) => {
          for (const child of element.children) {
            const box = child.getBoundingClientRect();
            if (box.height < 1 && getComputedStyle(child).display !== "contents") continue;
            const heading = child.querySelector("h1,h2,h3,[data-card-title]")?.textContent?.trim().slice(0, 50) ?? "";
            const name = child.getAttribute("aria-label") ?? heading;
            lines.push(`${"  ".repeat(depth)}${child.tagName.toLowerCase()} top=${Math.round(box.top + window.scrollY)} h=${Math.round(box.height)} ${name}`);
            if (depth < 2 && (child.classList.contains("space-y-6") || child.classList.contains("grid") || child.tagName === "MAIN")) {
              walk(child, depth + 1);
            }
          }
        };
        const main = document.querySelector("main")!;
        walk(main, 0);
        for (const child of main.querySelectorAll(":scope > div > div.space-y-6, :scope > div.space-y-6")) {
          lines.push("--- cards");
          walk(child, 1);
        }
        return lines.join("\n");
      });
      console.log(`\n### ${locale} ${raw}\n${report}`);
    }
  }
});

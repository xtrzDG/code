/**
 * The visual tests' first project (`visual-platform`, project.ts): the demo
 * owner signs in for the whole run (restaurant.ts), and the platform
 * admin's pages are taken before any other test adds accounts and
 * businesses to the platform they count, at 1440 px in the dark theme and
 * at 390 px in the light one, in Russian.
 */

import { ensureOnAdminTeam, signInAsPlatformAdmin } from "../support/admin";
import { TOUR_ADMIN_EMAIL } from "../support/env";
import { signInContext } from "../support/fixtures";
import { ru } from "../support/messages";
import { adminRoutes } from "../support/tour";
import { DESKTOP, PHONE } from "./clock";
import { signInRestaurantOwner } from "./restaurant";
import { shoot, test, type Shot } from "./shots";

test("the demo owner signs in for the run", async ({ request }) => {
  await signInRestaurantOwner(request);
});

/**
 * The reply time of the last hour is measured over the demo's seeded
 * replies, and which of them still fall within that hour depends on how
 * long the run took to get here.
 */
const lastHourReplies: Shot["mask"] = (page) => [
  page.getByRole("region", { name: ru.adminSystem.errorBudget.latency.title }),
];

/** "/admin/clients/business_…" → "admin-clients". */
function screenOf(path: string): string {
  return path.replace(/^\//, "").split("/").slice(0, 2).join("-");
}

for (const [screen, theme] of [
  [DESKTOP, "dark"],
  [PHONE, "light"],
] as const) {
  test.describe(`at ${screen.viewport.width} px`, () => {
    test.use(screen);

    test(`the platform admin's pages (${theme}, ru)`, async ({ page, request, context }) => {
      test.setTimeout(150_000);
      const restaurant = await signInRestaurantOwner(request);
      await ensureOnAdminTeam(request, TOUR_ADMIN_EMAIL);
      await signInContext(context, await signInAsPlatformAdmin(request, TOUR_ADMIN_EMAIL));
      for (const path of adminRoutes(restaurant.businessId)) {
        const mask = path === "/admin/system" ? lastHourReplies : undefined;
        await shoot(page, { name: screenOf(path), path, theme, locale: "ru", mask });
      }
    });
  });
}

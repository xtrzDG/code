/**
 * Every page of an owner's cabinet over the demo restaurant's data, in
 * Russian: at 1440 px in the dark theme and at 390 px in the light one
 * (README "Visual tests and the review gate"). The pages are the route
 * tour's (support/tour.ts) and the few it does not walk (customers, a
 * customer's card, integrations, deposits); the main screens in every theme
 * and language are in matrix-*.spec.ts.
 */

import type { Page } from "@playwright/test";

import { businessRoutes, settingsRoutes } from "../support/tour";
import { DESKTOP, PHONE } from "./clock";
import { conversationWith, customerNamed, openRestaurant, screenOf, type Restaurant } from "./restaurant";
import { shoot, test, type Shot, type Theme } from "./shots";

/** The audit log lists what this run's own visits did, at the times they did it. */
const auditEntries = (page: Page) => [page.locator("table tbody")];

/** Pages the route tour does not walk. */
async function morePages(restaurant: Restaurant, request: Parameters<typeof customerNamed>[0]): Promise<string[]> {
  const business = `/b/${restaurant.businessId}`;
  const customer = await customerNamed(request, restaurant, "Елена Петрова");
  const conversation = await conversationWith(request, restaurant, "Елена Петрова");
  return [
    `${business}/inbox/${conversation}`,
    `${business}/customers`,
    `${business}/customers/${customer}`,
    `${business}/customers/segments`,
  ];
}

function shotOf(restaurant: Restaurant, path: string, theme: Theme): Shot {
  // A conversation's and a customer's ids are new in every run.
  const stable = path.replace(/\/conversation_[\w-]+$/, "/conversation").replace(/\/contact_[\w-]+$/, "/customer");
  const name = screenOf(stable, restaurant.businessId);
  return { name, path, theme, locale: "ru", mask: path.endsWith("/settings/audit") ? auditEntries : undefined };
}

for (const [screen, theme] of [
  [DESKTOP, "dark"],
  [PHONE, "light"],
] as const) {
  test.describe(`at ${screen.viewport.width} px`, () => {
    test.use(screen);

    test(`the demo restaurant's business pages (${theme}, ru)`, async ({ page, request, context }) => {
      test.setTimeout(180_000);
      const restaurant = await openRestaurant(context);
      for (const path of [...businessRoutes(restaurant.businessId), ...(await morePages(restaurant, request))]) {
        await shoot(page, shotOf(restaurant, path, theme));
      }
    });

    test(`the demo restaurant's settings (${theme}, ru)`, async ({ page, context }) => {
      test.setTimeout(120_000);
      const restaurant = await openRestaurant(context);
      const settings = `/b/${restaurant.businessId}/settings`;
      for (const path of [...settingsRoutes(restaurant.businessId), `${settings}/integrations`, `${settings}/deposits`]) {
        await shoot(page, shotOf(restaurant, path, theme));
      }
    });
  });
}

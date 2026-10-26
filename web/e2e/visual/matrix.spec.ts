/**
 * The main screens in the full matrix: 1440 and 390 px, the dark and the
 * light theme, Russian, English and Georgian, over the demo restaurant
 * (README "Visual tests and the review gate"). A screen that
 * restaurant-pages.spec.ts takes at the same address (1440 dark and 390
 * light, in Russian) is not taken twice. The tunnel's finale is in
 * new-business.spec.ts.
 */

import { DESKTOP, PHONE } from "./clock";
import { conversationWith, openRestaurant } from "./restaurant";
import { MATRIX_LOCALES, shoot, test, THEMES, type Theme } from "./shots";

/** The main screens: their names and addresses inside the restaurant. */
function mainScreens(conversationId: string): { name: string; page: string; isOnEveryPage: boolean }[] {
  return [
    { name: "main-overview", page: "overview", isOnEveryPage: true },
    { name: "main-inbox-conversation", page: `inbox/${conversationId}`, isOnEveryPage: true },
    { name: "main-bookings-day", page: "bookings?view=day", isOnEveryPage: false },
    { name: "main-bookings-week", page: "bookings?view=week", isOnEveryPage: false },
    { name: "main-customers", page: "customers", isOnEveryPage: true },
    { name: "main-assistant-profile", page: "assistant/profile", isOnEveryPage: true },
    { name: "main-assistant-knowledge", page: "assistant/knowledge", isOnEveryPage: true },
    { name: "main-assistant-channels", page: "assistant/channels", isOnEveryPage: true },
    { name: "main-settings", page: "settings", isOnEveryPage: true },
    { name: "main-settings-billing", page: "settings/billing", isOnEveryPage: true },
  ];
}

for (const [screen, everyPageTheme] of [
  [DESKTOP, "dark"],
  [PHONE, "light"],
] as const satisfies readonly (readonly [typeof DESKTOP | typeof PHONE, Theme])[]) {
  test.describe(`at ${screen.viewport.width} px`, () => {
    test.use(screen);

    for (const locale of MATRIX_LOCALES) {
      test(`the main screens in both themes (${locale})`, async ({ page, request, context }) => {
        test.setTimeout(120_000);
        const restaurant = await openRestaurant(context);
        const conversation = await conversationWith(request, restaurant, "Елена Петрова");
        for (const theme of THEMES) {
          for (const main of mainScreens(conversation)) {
            // restaurant-pages.spec.ts has this one.
            if (main.isOnEveryPage && locale === "ru" && theme === everyPageTheme) {
              continue;
            }
            await shoot(page, { name: main.name, path: `/b/${restaurant.businessId}/${main.page}`, theme, locale });
          }
        }
      });
    }
  });
}

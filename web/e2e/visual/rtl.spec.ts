/**
 * The cabinet right to left: the demo restaurant's Hebrew conversation (Noa
 * books a table on WhatsApp) with the interface in Hebrew, at 1440 px in
 * the dark theme and at 390 px in the light one.
 */

import { DESKTOP, PHONE } from "./clock";
import { conversationWith, openRestaurant } from "./restaurant";
import { expect, shoot, test } from "./shots";

for (const [screen, theme] of [
  [DESKTOP, "dark"],
  [PHONE, "light"],
] as const) {
  test.describe(`at ${screen.viewport.width} px`, () => {
    test.use(screen);

    test(`a Hebrew conversation, right to left (${theme})`, async ({ page, request, context }) => {
      const restaurant = await openRestaurant(context);
      const conversation = await conversationWith(request, restaurant, "נועה כהן");
      await shoot(page, {
        name: "rtl-conversation",
        path: `/b/${restaurant.businessId}/inbox/${conversation}`,
        theme,
        locale: "he",
      });
      await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    });
  });
}

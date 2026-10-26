/**
 * The public pages of the route tour (support/tour.ts) without a session,
 * with the demo restaurant's hosted chat page and its notice, in Russian at
 * 1440 px dark and 390 px light. The landing page, the help center and the
 * status page are reading pages: the gate lets them be longer than four
 * phone screens.
 */

import { chatPageRoutes, PUBLIC_ROUTES } from "../support/tour";
import { DESKTOP, PHONE } from "./clock";
import { openRestaurant } from "./restaurant";
import { shoot, test } from "./shots";

/** "/help/whats-new" → "public-help-whats-new", "/c/mtsvane-ezo" → "public-chat-page". */
function screenOf(path: string, slug: string): string {
  const page = path.replace(`/c/${slug}`, "/chat-page").replace(/^\//, "");
  return ["public", ...(page ? page.split("/") : ["landing"])].join("-");
}

/** Pages people use (sign-in, a chat), not reading pages. */
const APP_PAGES = new Set(["/login"]);

for (const [screen, theme] of [
  [DESKTOP, "dark"],
  [PHONE, "light"],
] as const) {
  test.describe(`at ${screen.viewport.width} px`, () => {
    test.use(screen);

    test(`the public pages (${theme}, ru)`, async ({ page, context }) => {
      test.setTimeout(120_000);
      const { slug } = await openRestaurant(context);
      await context.clearCookies({ name: "aw_session" });
      for (const path of [...PUBLIC_ROUTES, ...chatPageRoutes(slug)]) {
        const isChatPage = path === `/c/${slug}`;
        await shoot(page, {
          name: screenOf(path, slug),
          path,
          theme,
          locale: "ru",
          isDocument: !APP_PAGES.has(path) && !isChatPage,
        });
      }
    });
  });
}

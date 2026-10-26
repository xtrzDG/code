/**
 * The route tour, part two: an owner's business pages, read from Tbilisi in
 * English and again in Hebrew (support/tour.ts explains the double visit).
 */

import { test } from "./support/fixtures";
import { businessRoutes, readIn, TOUR_LOCALES, TOUR_TIMEOUT_MS, visitTwice } from "./support/tour";

test.describe.configure({ timeout: TOUR_TIMEOUT_MS });

for (const locale of TOUR_LOCALES) {
  test(`an owner's business pages (${locale})`, async ({ page, owner }) => {
    await readIn(page, locale);
    for (const path of businessRoutes(owner.businessId)) {
      await visitTwice(page, path);
    }
  });
}

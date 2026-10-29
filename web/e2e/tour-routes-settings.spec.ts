/**
 * The route tour, part three: an owner's settings and account pages, read
 * from Tbilisi in English and again in Italian (support/tour.ts explains
 * the double visit).
 */

import { test } from "./support/fixtures";
import { expectReaderZone, readIn, settingsRoutes, TOUR_LOCALES, TOUR_TIMEOUT_MS, visitTwice } from "./support/tour";

test.describe.configure({ timeout: TOUR_TIMEOUT_MS });

for (const locale of TOUR_LOCALES) {
  test(`an owner's settings and account pages (${locale})`, async ({ page, owner }) => {
    await readIn(page, locale);
    for (const path of settingsRoutes(owner.businessId)) {
      await visitTwice(page, path);
    }
    // Account → Security: its dates are the reader's (React #418 here was the tour's finding).
    await expectReaderZone(page);
  });
}

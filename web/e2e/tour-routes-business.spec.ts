/**
 * The route tour, part two: an owner's business pages, read from Tbilisi in
 * English and again in Hebrew (support/tour.ts explains the double visit).
 */

import { test } from "./support/fixtures";
import { readIn, TOUR_LOCALES, TOUR_TIMEOUT_MS, visitTwice } from "./support/tour";

test.describe.configure({ timeout: TOUR_TIMEOUT_MS });

for (const locale of TOUR_LOCALES) {
  test(`an owner's business pages (${locale})`, async ({ page, owner }) => {
    await readIn(page, locale);
    const business = `/b/${owner.businessId}`;
    for (const path of [
      "/businesses",
      `${business}/overview`,
      `${business}/overview/reports`,
      `${business}/inbox`,
      `${business}/inbox?view=all`,
      `${business}/bookings`,
      `${business}/bookings/waitlist`,
      `${business}/bookings/return-visits`,
      `${business}/assistant`,
      `${business}/assistant/versions`,
      `${business}/assistant/checks`,
      `${business}/assistant/knowledge`,
      `${business}/assistant/knowledge/questions`,
      `${business}/assistant/knowledge/resources`,
      `${business}/assistant/knowledge/import`,
      `${business}/assistant/profile`,
      `${business}/assistant/channels`,
      `${business}/assistant/channels/website`,
      `${business}/assistant/channels/calls`,
      `${business}/assistant/channels/share`,
    ]) {
      await visitTwice(page, path);
    }
  });
}

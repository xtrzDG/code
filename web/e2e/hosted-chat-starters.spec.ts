/**
 * Starter chips on the hosted chat page in the visitor's own language
 * (against the real API): a business whose FAQ has no ready questions yet
 * gets its niche's ready questions in English, Russian and Georgian, and
 * never a chip in another language than the chat's.
 */

import { expect, test } from "./support/fixtures";
import { openChatBusiness } from "./support/hosted-chat";

const CHIPS = [
  { locale: "en-US", language: "en", chip: "How can I book a table?", other: "Как забронировать стол?" },
  { locale: "ru-RU", language: "ru", chip: "Как забронировать стол?", other: "How can I book a table?" },
  { locale: "ka-GE", language: "ka", chip: "როგორ დავჯავშნო მაგიდა?", other: "Как забронировать стол?" },
];

for (const { locale, language, chip, other } of CHIPS) {
  test.describe(`a visitor reading ${language}`, () => {
    test.use({ locale });

    test(`sees the restaurant's ready questions in ${language}`, async ({ page, request, account }) => {
      const business = await openChatBusiness(request, account.token, ["en", "ru", "ka"]);

      await page.goto(`/c/${business.slug}`);

      await expect(page.locator("main")).toHaveAttribute("lang", language);
      await expect(page.getByRole("button", { name: chip })).toBeVisible();
      await expect(page.getByRole("button", { name: other })).toHaveCount(0);
    });
  });
}

/**
 * Booking times in the cabinet's own clock: in a Russian or Georgian
 * cabinet the new booking's time reads "08:00" (a 24-hour clock, no AM or
 * PM) and its date puts the day first (never mm/dd/yyyy), whatever the
 * browser's own language is.
 */

import { WEB_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { ka, ru } from "./support/messages";
import { waitForNetworkQuiet } from "./support/network";
import { expectTime, shownTime, timeField, typeTime } from "./support/timeField";

const DICTIONARIES = { ru, ka } as const;

for (const [locale, texts] of Object.entries(DICTIONARIES)) {
  test(`a new booking's time reads 08:00 and its date puts the day first (${locale})`, async ({ page, owner, context }) => {
    await context.addCookies([{ name: "aw_locale", value: locale, url: WEB_URL, sameSite: "Lax" }]);
    await page.goto(`/b/${owner.businessId}/bookings`);
    await waitForNetworkQuiet(page);
    await page.getByRole("button", { name: texts.bookings.newBooking }).first().click();
    const form = page.getByRole("dialog", { name: texts.bookings.form.title });
    await expect(form).toBeVisible();

    const time = timeField(form, new RegExp(`^${texts.bookings.form.time}\\*?$`));
    // Hours and minutes only: no AM/PM segment in this language.
    await expect(time.getByRole("spinbutton")).toHaveCount(2);
    await typeTime(time, "08:00");
    await expectTime(time, "08:00");
    expect(await shownTime(time)).toBe("08:00");
    await expect(time.getByRole("spinbutton").first()).toHaveAttribute("aria-valuetext", "08:00");

    const year = new Date().getFullYear() + 1;
    const date = form.getByLabel(texts.bookings.form.date);
    await date.fill(`${year}-03-03`);
    await date.blur();
    await expect(date).toHaveValue(new RegExp(`^3 \\S+ ${year}`));
    await expect(date).not.toHaveValue(/\d{1,2}\/\d{1,2}\/\d{2,4}/);
  });
}

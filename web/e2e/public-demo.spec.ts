import { expect, test } from "./support/fixtures";
import { DEMO_RESTAURANT } from "./support/demo";
import { en } from "./support/messages";

/**
 * The landing page's live demo and value calculator. The suite's API runs
 * the seeded demo businesses as the public demos (SEED_DEMO_DATA without
 * PUBLIC_DEMO_BUSINESS_IDS) and the rehearsal model (LLM_PROVIDER=scripted):
 * every demo turn is a sandbox turn, so a booking is only shown as one.
 */
test.describe("the landing page's live demo", () => {
  test("answers a visitor in sandbox and says what would happen", async ({ page }) => {
    await page.goto("/en");
    const chat = page.getByTestId("demo-chat");
    await expect(chat.getByText(DEMO_RESTAURANT).first()).toBeVisible();
    await expect(chat.getByText(en.publicDemo.sandbox)).toBeVisible();

    // A starter in the visitor's language sends itself.
    await chat.getByRole("button", { name: en.publicDemo.genericStarters.hours }).click();
    await expect(chat.locator("[data-role='assistant']")).toHaveCount(1, { timeout: 30_000 });

    await chat.getByLabel(en.publicDemo.inputLabel).fill("Can I book a table for 4 tomorrow at 8pm?");
    await chat.getByRole("button", { name: en.publicDemo.send }).click();
    await expect(chat.locator("[data-role='assistant']")).toHaveCount(2, { timeout: 30_000 });
    await expect(chat.getByTestId("demo-outcome-booking")).toHaveText(en.publicDemo.outcomes.booking);

    // Starting over forgets the conversation.
    await chat.getByRole("button", { name: en.publicDemo.restart }).click();
    await expect(chat.locator("[data-role='assistant']")).toHaveCount(0);
  });

  test("counts what missed requests are worth against the plan", async ({ page }) => {
    await page.goto("/en?country=DE");
    const calculator = page.getByTestId("roi-calculator");
    await calculator.scrollIntoViewIfNeeded();
    await calculator.getByLabel(new RegExp(en.roi.check)).fill("50");
    // 120 missed × 40 % after hours × 30 % booking × €50 = €720 a month.
    await expect(page.getByTestId("roi-value")).toHaveText("€720");
    await expect(page.getByTestId("roi-multiple")).toContainText("×");

    await calculator.getByLabel(new RegExp(en.roi.check)).fill("");
    await expect(page.getByTestId("roi-result")).toContainText(en.roi.noCheck);
  });
});

import { expect, test } from "./support/fixtures";
import { API_URL } from "./support/env";

test("the website chat demo page shows the widget of a business", async ({ page, owner }) => {
  await page.goto(`${API_URL}/widget/demo?business_id=${encodeURIComponent(owner.businessId)}`);
  await expect(page.getByRole("heading", { level: 1, name: "Website chat demo" })).toBeVisible();
  await expect(page.getByText(owner.businessId).first()).toBeVisible();

  // The demo opens the chat at once (data-open) in preview mode: the website
  // chat is not switched on for a new business yet.
  const launcher = page.getByRole("button", { name: "Close chat", expanded: true });
  await expect(launcher).toBeVisible();
  await expect(page.getByText(/Preview: this chat is switched off/)).toBeVisible();
  await expect(page.getByRole("textbox")).toBeVisible();

  await launcher.click();
  await expect(page.getByRole("button", { name: "Open chat", expanded: false })).toBeVisible();
  await expect(page.getByRole("textbox")).toBeHidden();
});

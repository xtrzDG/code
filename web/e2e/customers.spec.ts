/**
 * Customers against the real API:
 *
 *  - the owner finds a customer, tags them and marks them VIP on their
 *    page, blocks them, saves a segment (a blocked customer never belongs)
 *    and, once they are unblocked, sees them in it and downloads its CSV;
 *  - staff see the customer's phone masked until an owner lets the team
 *    see phone numbers;
 *  - a conversation's header says who the customer is ("New customer")
 *    and leads to their page;
 *  - Settings → Privacy keeps a link to the customers' data requests.
 */

import { inviteStaff, signInByEmail, uniqueEmail, uniqueSuffix } from "./support/api";
import { bookedCustomer } from "./support/customers";
import { signInAsDemoOwner, visitorAsksForPerson } from "./support/demo";
import { expect, signInContext, test } from "./support/fixtures";
import { waitingConversationOf } from "./support/inbox";
import { en } from "./support/messages";

const customers = en.customers;
const segments = en.segments;

test.describe.configure({ timeout: 120_000 });

test("the owner tags a customer, marks them VIP, blocks them and gathers a segment", async ({ page, request, owner }) => {
  const nino = await bookedCustomer(request, owner.token, owner.businessId, { name: "Nino Beridze", phone: "+995599123456" });

  await page.goto(`/b/${owner.businessId}/customers`);
  await page.getByRole("link", { name: /Nino Beridze/ }).click();
  await expect(page).toHaveURL(new RegExp(`/customers/${nino.contactId}$`));
  await expect(page.getByRole("heading", { name: "Nino Beridze" }).first()).toBeVisible();
  await expect(page.getByRole("list", { name: customers.timeline.title })).toContainText(customers.timeline.booking);

  await test.step("tags and the VIP mark", async () => {
    await page.getByLabel(customers.card.addTag).fill("Regular");
    await page.keyboard.press("Enter");
    await expect(page.getByRole("list", { name: customers.card.tags })).toContainText("Regular");
    const vip = page.getByRole("switch", { name: customers.card.vip });
    await vip.click();
    await expect(vip).toHaveAttribute("aria-checked", "true");
  });

  await test.step("blocking asks first", async () => {
    await page.getByRole("button", { name: customers.block.action }).click();
    const dialog = page.getByRole("dialog", { name: customers.block.confirmTitle.replace("{name}", "Nino Beridze") });
    await dialog.getByRole("button", { name: customers.block.confirm, exact: true }).click();
    await expect(page.getByText(customers.block.blocked.replace("{name}", "Nino Beridze"))).toBeVisible();
    await expect(page.getByRole("button", { name: customers.block.unblock })).toBeVisible();
  });

  await test.step("the list filters VIPs and blocked customers, tags without case", async () => {
    // The page's own way back (the sidebar and the section's tabs name the list too).
    await page.getByRole("link", { name: customers.detail.back }).last().click();
    await page.getByRole("group", { name: customers.list.filter }).getByText(customers.list.filters.blocked, { exact: true }).click();
    await expect(page).toHaveURL(/show=blocked/);
    await expect(page.getByRole("link", { name: /Nino Beridze/ })).toBeVisible();
    await page.getByRole("combobox", { name: customers.list.tag }).selectOption("Regular");
    await expect(page).toHaveURL(/tag=Regular/);
    await expect(page.getByRole("link", { name: /Nino Beridze/ })).toBeVisible();
  });

  await test.step("a segment leaves blocked customers out", async () => {
    await page.goto(`/b/${owner.businessId}/customers/segments`);
    await page.getByRole("button", { name: segments.new }).first().click();
    const editor = page.getByRole("dialog", { name: segments.editor.newTitle });
    await editor.getByLabel(segments.editor.name).fill("Regulars");
    await editor.getByLabel(segments.editor.tag).fill("regular");
    await expect(editor.getByRole("status")).toHaveText(segments.preview.none);
    await editor.getByRole("button", { name: segments.editor.save }).click();
    await expect(page.getByText(segments.saved)).toBeVisible();
    await page.getByRole("button", { name: segments.members }).click();
    await expect(page.getByText(segments.noMembers)).toBeVisible();
  });

  await test.step("unblocked, the customer is in the segment and its CSV", async () => {
    await page.goto(`/b/${owner.businessId}/customers/${nino.contactId}`);
    await page.getByRole("button", { name: customers.block.unblock }).click();
    await expect(page.getByText(customers.block.unblocked.replace("{name}", "Nino Beridze"))).toBeVisible();
    await page.goto(`/b/${owner.businessId}/customers/segments`);
    await page.getByRole("button", { name: segments.members }).click();
    await expect(page.getByRole("link", { name: /Nino Beridze/ })).toBeVisible();
    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: segments.export }).click();
    expect((await download).suggestedFilename()).toMatch(/\.csv$/);
  });
});

test("staff see a customer's phone masked until an owner lets them", async ({ browser, page, request, owner }) => {
  await bookedCustomer(request, owner.token, owner.businessId, { name: "Giorgi Kapanadze", phone: "+995577123456" });
  const staffEmail = uniqueEmail();
  await inviteStaff(request, owner.token, owner.businessId, staffEmail);
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  await signInContext(context, await signInByEmail(request, staffEmail));
  const staff = await context.newPage();

  await staff.goto(`/b/${owner.businessId}/customers`);
  const row = staff.getByRole("link", { name: /Giorgi Kapanadze/ });
  await expect(row).toContainText("+995 ••• ••• •56");
  await expect(row).not.toContainText("577");
  // The switch is the owners'.
  await expect(staff.getByRole("switch", { name: customers.access.staffPhones })).toHaveCount(0);

  await page.goto(`/b/${owner.businessId}/customers`);
  await expect(page.getByRole("link", { name: /Giorgi Kapanadze/ })).toContainText(/577\s?12\s?34\s?56/);
  await page.getByRole("switch", { name: customers.access.staffPhones }).click();
  await expect(page.getByText(customers.access.on)).toBeVisible();

  await staff.reload();
  await expect(row).toContainText(/577\s?12\s?34\s?56/);
  await context.close();
});

test("a conversation's header names the customer's standing and opens their page", async ({ page, request }) => {
  const owner = await signInAsDemoOwner(request);
  await signInContext(page.context(), owner.token);
  const visitor = await visitorAsksForPerson(request, owner.businessId, `Standing visitor ${uniqueSuffix()}`);
  const conversationId = await waitingConversationOf(request, owner.token, owner.businessId, visitor.name);

  await page.goto(`/b/${owner.businessId}/inbox/${conversationId}`);
  const standing = page.getByRole("link", { name: customers.standing.open.replace("{line}", customers.standing.new) });
  await expect(standing).toHaveText(customers.standing.new);
  await standing.click();
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/customers/contact_`));
  await expect(page.getByRole("heading", { name: visitor.name }).first()).toBeVisible();
  await expect(page.getByRole("list", { name: customers.timeline.title })).toContainText(customers.timeline.conversation);
});

test("Settings → Privacy leads to the customers' data requests", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/settings/privacy`);
  await page.getByRole("link", { name: customers.privacyLink.link }).click();
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/customers$`));
});

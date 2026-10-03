/**
 * Settings → Notifications: staff contacts are checked and show how
 * notifications reach them; this device turns on through the browser's
 * Push API (mocked, subscribed at a local push service the test starts),
 * gets an encrypted test whose link opens the cabinet, and turns off.
 */

import type { APIRequestContext } from "@playwright/test";

import { API_URL } from "./support/env";
import { expect, test, type Owner } from "./support/fixtures";
import { en } from "./support/messages";
import { decryptPush, mockBrowserPush, newReceiver, startPushService } from "./support/push";

async function saveContacts(request: APIRequestContext, owner: Owner, contacts: Record<string, unknown>[]): Promise<void> {
  const response = await request.patch(`${API_URL}/v1/businesses/${owner.businessId}`, {
    data: { manager_contacts: contacts },
    headers: { authorization: `Bearer ${owner.token}` },
  });
  expect(response.status(), await response.text()).toBe(200);
}

const fill = (template: string, values: Record<string, string>) =>
  template.replace(/\{(\w+)\}/g, (placeholder, name: string) => values[name] ?? placeholder);

test("the owner checks staff contacts and sees how notifications reach them", async ({ page, owner, request }) => {
  await saveContacts(request, owner, [
    {
      name: "Anna",
      channel: "email",
      address: "anna@salon.example",
      language: "en",
      preferences: { events: ["handoff"], quiet_hours: { starts_at: "22:00", ends_at: "08:00" } },
    },
    { name: "Levan", channel: "telegram", address: "777000111", language: "en" },
  ]);
  await page.goto(`/b/${owner.businessId}/settings/notifications`);

  const anna = page.getByRole("listitem").filter({ hasText: "anna@salon.example" });
  const levan = page.getByRole("listitem").filter({ hasText: "Levan" });
  await expect(anna.getByText("Only: handoffs · quiet 22:00–08:00")).toBeVisible();
  // A Telegram chat is named, never shown by its numeric id.
  await expect(levan.getByText(en.notifications.contacts.telegramChat)).toBeVisible();
  await expect(levan).not.toContainText("777000111");
  await expect(levan.getByText(en.notifications.contacts.providerMissing)).toBeVisible();

  // E-mail without SMTP outside production is written to the log: delivered.
  await anna.getByRole("button", { name: fill(en.notifications.contacts.testLabel, { name: "Anna" }) }).click();
  await expect(page.getByText(fill(en.notifications.contacts.testSimulated, { name: "Anna" }))).toBeVisible();
  await expect(anna.getByText(en.notifications.contacts.status.delivered, { exact: true })).toBeVisible();

  // Telegram without the platform bot cannot deliver: no test to send, and why.
  const levanTest = levan.getByRole("button", { name: fill(en.notifications.contacts.testLabel, { name: "Levan" }) });
  await expect(levanTest).toBeDisabled();
  const reason = fill(en.notifications.contacts.testUnavailable, { channel: en.settings.contacts.channels.telegram });
  await expect(levanTest).toHaveAccessibleDescription(reason);
  await expect(levan.getByText(reason)).toBeVisible();

  // The contact's quiet hours are switched off in its dialog.
  await anna.getByRole("button", { name: fill(en.settings.contacts.editLabel, { name: "Anna" }) }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("checkbox", { name: en.notifications.preferences.quietHoursToggle }).uncheck();
  await dialog.getByRole("button", { name: en.common.save }).click();
  await expect(anna.getByText("Only: handoffs", { exact: true })).toBeVisible();
});

test("this device turns on, gets an encrypted test whose link opens the cabinet, and turns off", async ({ page, owner }) => {
  const pushService = await startPushService();
  const receiver = newReceiver();
  await mockBrowserPush(page, pushService.endpoint, receiver);
  try {
    await page.goto(`/b/${owner.businessId}/settings/notifications`);
    const card = page.getByRole("region", { name: en.notifications.device.title });
    await expect(card.getByText(en.notifications.device.off, { exact: true })).toBeVisible();

    await card.getByRole("button", { name: en.notifications.device.enable }).click();
    await expect(page.getByText(en.notifications.device.enabled)).toBeVisible();
    await expect(card.getByText(en.notifications.device.on, { exact: true })).toBeVisible();

    await card.getByRole("button", { name: en.notifications.device.test }).click();
    await expect(page.getByText(en.notifications.device.testDelivered)).toBeVisible();
    await expect(card.getByText(/^Last notification /)).toBeVisible();

    const [posted] = pushService.received;
    expect(posted?.headers["content-encoding"]).toBe("aes128gcm");
    expect(posted?.headers.authorization).toMatch(/^vapid t=[\w-]+\.[\w-]+\.[\w-]+, k=[\w-]+$/);
    expect(posted?.headers.topic).toBeTruthy();
    const message = JSON.parse(decryptPush(posted!.body, receiver)) as Record<string, string>;
    expect(message.title).toBe(`Test notification · ${owner.businessName}`);
    expect(message.tag).toBe("check:notifications");
    expect(message.url).toMatch(/\/n\/[\w-]+$/);

    // The notification's link opens the notification settings (signed in already).
    await page.goto(message.url!);
    await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/settings/notifications$`));

    await page.getByRole("region", { name: en.notifications.device.title }).getByRole("button", { name: en.notifications.device.disable }).click();
    await expect(page.getByText(en.notifications.device.disabled)).toBeVisible();
  } finally {
    await pushService.close();
  }
});

test("a link that was altered or is not for this account explains itself", async ({ page, owner }) => {
  await page.goto(`/n/${"A".repeat(67)}`);
  await expect(page.getByText(en.notifications.link.invalidTitle)).toBeVisible();
  await page.getByRole("link", { name: en.notifications.link.toBusinesses }).click();
  await expect(page.getByText(owner.businessName)).toBeVisible();
});

test("my events and quiet hours are saved for my devices", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/settings/notifications`);
  const card = page.getByRole("region", { name: en.notifications.mine.title });
  await expect(card.getByRole("heading", { name: en.notifications.mine.title })).toBeVisible();

  await card.getByRole("checkbox", { name: en.notifications.preferences.event.lead }).uncheck();
  await card.getByRole("checkbox", { name: en.notifications.preferences.quietHoursToggle }).check();
  await card.getByLabel(en.notifications.preferences.quietUntil).fill("22:00");
  await card.getByRole("button", { name: en.notifications.mine.save }).click();
  await expect(card.getByText(en.notifications.preferences.errors.same)).toBeVisible();

  await card.getByLabel(en.notifications.preferences.quietUntil).fill("07:30");
  await card.getByRole("button", { name: en.notifications.mine.save }).click();
  await expect(page.getByText(en.notifications.mine.saved)).toBeVisible();
  await page.reload();
  await expect(card.getByRole("checkbox", { name: en.notifications.preferences.event.lead })).not.toBeChecked();
  await expect(card.getByLabel(en.notifications.preferences.quietUntil)).toHaveValue("07:30");
});

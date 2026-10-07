/**
 * The guided parts of the Channels page: connecting Telegram through
 * @BotFather with the pasted key checked before it is saved (Telegram's
 * answers are served by the test: the suite never reaches Telegram), and
 * the live preview of the website chat, framed from the hosted chat page,
 * in the owner's language and following the chosen corner at once.
 */

import { BERLIN_SALON, expect, test } from "./support/fixtures";
import { WEB_URL } from "./support/env";
import { openChatBusiness } from "./support/hosted-chat";
import { en, ka } from "./support/messages";

/** A stand-in with a real key's shape and no secret in it. */
const BOT_TOKEN = `123456789:${"a".repeat(35)}`;
/** A 1×1 PNG: the bot's photo as the API inlines it. */
const BOT_PHOTO =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";

test("an owner connects Telegram step by step and sees the bot before connecting it", async ({ page, owner, consoleErrors }) => {
  consoleErrors.allow(/status of 422/);
  const checked: string[] = [];
  await page.route(`**/api/backend/v1/businesses/${owner.businessId}/channels/telegram/validate-token`, (route) => {
    const { bot_token: token } = route.request().postDataJSON() as { bot_token: string };
    checked.push(token);
    return token === BOT_TOKEN
      ? route.fulfill({ json: { username: "salon_morgenrot_bot", display_name: "Salon Morgenrot", avatar_data_url: BOT_PHOTO } })
      : route.fulfill({
          status: 422,
          json: {
            error: "validation_failed",
            message: "Telegram did not accept the bot token.",
            reasons: [{ code: "telegram_token_rejected", message: "Telegram did not accept the bot token.", details: [] }],
          },
        });
  });
  const connected: unknown[] = [];
  await page.route(`**/api/backend/v1/businesses/${owner.businessId}/channels/telegram`, (route) => {
    connected.push(route.request().postDataJSON());
    return route.fulfill({
      json: {
        id: "channel_7e1d2c3b-4a59-4f6e-8d7c-6b5a4f3e2d1c",
        business_id: owner.businessId,
        channel: "telegram",
        status: "connected",
        account_id: "salon_morgenrot_bot",
        has_credential: true,
        updated_at: Date.now() * 1000,
      },
    });
  });

  await page.goto(`/b/${owner.businessId}/assistant/channels`);
  const card = page.getByRole("region", { name: en.channels.kinds.telegram, exact: true });
  await card.getByRole("button", { name: `${en.channels.connect} — ${en.channels.kinds.telegram}` }).click();
  const dialog = page.getByRole("dialog");

  await expect(dialog.getByRole("link", { name: en.channelSetup.telegram.openBotFather })).toHaveAttribute(
    "href",
    "https://t.me/BotFather",
  );
  await expect(dialog.getByText("/newbot", { exact: true })).toBeVisible();
  await expect(dialog.getByText(BERLIN_SALON.name, { exact: true })).toBeVisible();
  await expect(dialog.getByText("salon_morgenrot_bot", { exact: true })).toBeVisible();
  const connect = dialog.getByRole("button", { name: en.channelSetup.telegram.connect });
  await expect(connect).toBeDisabled();

  const key = dialog.getByLabel(en.channelSetup.telegram.tokenLabel);
  await key.fill("not a key at all");
  await expect(dialog.getByText(en.channelSetup.telegram.format)).toBeVisible();
  await key.fill(`123456789:${"b".repeat(35)}`);
  await expect(dialog.getByText(en.channelSetup.telegram.rejected)).toBeVisible();
  await expect(connect).toBeDisabled();

  // A copy brings line breaks along; the key is checked without them.
  await key.fill(` ${BOT_TOKEN}\n`);
  const bot = dialog.getByRole("status");
  await expect(bot.getByText(en.channelSetup.telegram.found)).toBeVisible();
  await expect(bot.getByText("Salon Morgenrot", { exact: true })).toBeVisible();
  await expect(bot.getByRole("img", { name: "Photo of @salon_morgenrot_bot" })).toBeVisible();
  expect(checked).toEqual([`123456789:${"b".repeat(35)}`, BOT_TOKEN]);

  await dialog.getByRole("button", { name: "Connect @salon_morgenrot_bot" }).click();
  await expect(page.getByText("Telegram connected")).toBeVisible();
  await expect(dialog).toBeHidden();
  expect(connected).toEqual([{ bot_token: BOT_TOKEN }]);
});

test.describe("for an owner who reads Georgian", () => {
  test("the live preview speaks Georgian and follows the chosen corner at once", async ({
    page,
    context,
    request,
    account,
    consoleErrors,
  }) => {
    // The website chat's embed code needs APP_BASE_URL, which the suite's API does not set.
    consoleErrors.allow(/status of 502 \(Bad Gateway\).*\/channels\/web\/snippet/);
    const business = await openChatBusiness(request, account.token);
    await context.addCookies([{ name: "aw_locale", value: "ka", url: WEB_URL, sameSite: "Lax" }]);

    await page.goto(`/b/${business.id}/assistant/channels`);
    const preview = page.frameLocator(`iframe[title="${ka.channelSetup.preview.frameTitle}"]`);

    // The guide (docs/LAUNCH.md) sends the owner to the preview by its heading.
    await expect(page.getByRole("region", { name: ka.channelSetup.preview.title })).toBeVisible();
    await expect(page.getByRole("button", { name: "ქართული" })).toHaveAttribute("aria-pressed", "true");
    await expect(preview.getByRole("textbox")).toHaveAttribute("placeholder", "დაწერეთ შეტყობინება…");
    await expect(preview.locator(".aw")).toHaveAttribute("lang", "ka");

    // Before anything is saved, the corner moves and the language changes in the frame.
    await page.getByRole("radio", { name: ka.channels.widget.positionLeft }).check();
    await expect(preview.locator(".aw")).toHaveClass(/aw-left/);
    await page.getByRole("button", { name: "ინგლისური" }).click();
    await expect(preview.getByRole("textbox")).toHaveAttribute("placeholder", "Type a message…");
  });

  test("only the preview of the hosted chat page may be framed, and only by the cabinet", async ({ request, account }) => {
    const business = await openChatBusiness(request, account.token);

    const preview = await request.get(`${WEB_URL}/c/${business.slug}?preview=1&lang=ka`);
    const plain = await request.get(`${WEB_URL}/c/${business.slug}`);

    expect(preview.headers()["x-frame-options"]).toBe("SAMEORIGIN");
    expect(preview.headers()["content-security-policy"]).toContain("frame-ancestors 'self'");
    expect(plain.headers()["x-frame-options"]).toBe("DENY");
    expect(plain.headers()["content-security-policy"]).toContain("frame-ancestors 'none'");
  });
});

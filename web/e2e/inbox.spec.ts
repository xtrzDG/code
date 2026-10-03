/**
 * The team inbox at work, against the real API and the demo restaurant
 * (support/demo.ts), whose visitors' chats the assistant hands to a person:
 *
 *  - a staff member's phone gets the notification; its link opens the
 *    conversation with the reply box in sight, so they answer and resolve
 *    without scrolling, and the visitor's chat gets the answer;
 *  - two people take the same conversation at once: the second is told
 *    and sees who has it;
 *  - the team's notes never reach the customer's chat or the transcript.
 */

import type { APIRequestContext, Browser, BrowserContext, Page } from "@playwright/test";

import { inviteStaff, signInByEmail, uniqueEmail, uniqueSuffix } from "./support/api";
import { signInAsDemoOwner, visitorAsksForPerson, visitorTranscript, type DemoOwner } from "./support/demo";
import { expect, signInContext, test } from "./support/fixtures";
import { assignByApi, cardOf, subscribeDevice, userIdOf, waitingConversationOf } from "./support/inbox";
import { en } from "./support/messages";
import { decryptPush, newReceiver, startPushService } from "./support/push";

test.describe.configure({ timeout: 120_000 });

const PHONE = { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } as const;

interface Staff {
  token: string;
  context: BrowserContext;
  page: Page;
}

/** A new staff member of the demo restaurant, signed in in a browser of their own. */
async function newStaff(browser: Browser, request: APIRequestContext, owner: DemoOwner, device = {}): Promise<Staff> {
  const email = uniqueEmail();
  await inviteStaff(request, owner.token, owner.businessId, email);
  const token = await signInByEmail(request, email);
  const context = await browser.newContext({ reducedMotion: "reduce", serviceWorkers: "block", locale: "en-US", ...device });
  await signInContext(context, token);
  return { token, context, page: await context.newPage() };
}

function replyBox(page: Page) {
  return page.getByRole("textbox", { name: en.conversations.reply.label });
}

test("staff open a notification's link on a phone, reply without scrolling and resolve the handoff", async ({ browser, request }) => {
  const owner = await signInAsDemoOwner(request);
  const staff = await newStaff(browser, request, owner, PHONE);
  const pushService = await startPushService();
  const receiver = newReceiver();
  try {
    await subscribeDevice(request, staff.token, owner.businessId, pushService.endpoint, receiver);
    const visitor = await visitorAsksForPerson(request, owner.businessId, `Inbox visitor ${uniqueSuffix()}`);

    // The handoff reaches the staff member's phone; its link leads into the cabinet.
    await expect.poll(() => pushService.received.length, { timeout: 30_000 }).toBeGreaterThan(0);
    const notification = JSON.parse(decryptPush(pushService.received[0]!.body, receiver)) as { url: string };
    expect(notification.url).toMatch(/\/n\/[\w-]+$/);
    const { page } = staff;
    await page.goto(notification.url);
    await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/inbox/conversation_`));
    await expect(page.getByRole("heading", { level: 2, name: visitor.name })).toBeVisible();

    // The reply box and the quick actions are on the first screen: no scrolling.
    const box = replyBox(page);
    await expect(box).toBeInViewport();
    const resolve = page.getByRole("button", { name: en.inboxCard.actions.resolve, exact: true });
    await expect(resolve).toBeInViewport();
    const reply = `Hello, I am the manager on duty. ${uniqueSuffix()}`;
    await box.fill(reply);
    const send = page.getByRole("button", { name: en.inboxCard.composer.sendLabel, exact: true });
    await expect(send).toBeInViewport();
    await send.click();
    await expect(page.getByRole("region", { name: en.conversations.transcript }).getByText(reply)).toBeVisible();
    await expect(box).toHaveValue("");
    await expect.poll(() => visitorTranscript(request, owner.businessId, visitor)).toContain(reply);

    // Resolving gives the conversation back to the assistant.
    await expect(resolve).toBeInViewport();
    await resolve.click();
    const confirm = page.getByRole("alertdialog").or(page.getByRole("dialog"));
    await confirm.getByRole("button", { name: en.inboxCard.resolveConfirm.confirm, exact: true }).click();
    await expect(page.getByText(en.inboxCard.resolved)).toBeVisible();
    await expect(resolve).toHaveCount(0);
    const conversationId = new URL(page.url()).pathname.split("/").at(-1)!;
    const card = await cardOf(request, owner.token, owner.businessId, conversationId);
    expect(card.handoffs.map((handoff) => handoff.status)).not.toContain("open");
  } finally {
    await pushService.close();
    await staff.context.close();
  }
});

test("when someone else took the conversation a moment earlier, staff are told and see who has it", async ({ browser, request }) => {
  const owner = await signInAsDemoOwner(request);
  const staff = await newStaff(browser, request, owner, { viewport: { width: 1280, height: 900 } });
  try {
    const visitor = await visitorAsksForPerson(request, owner.businessId, `Inbox visitor ${uniqueSuffix()}`);
    const conversationId = await waitingConversationOf(request, owner.token, owner.businessId, visitor.name);
    const ownerId = await userIdOf(request, owner.token);
    const { page } = staff;
    await page.goto(`/b/${owner.businessId}/inbox/${conversationId}`);
    const assignButton = page.getByRole("button", { name: new RegExp(`^${en.inbox.assign.nobody}\\.`) });
    await expect(assignButton).toBeVisible();

    // The owner takes it just before the staff member's choice reaches the API.
    let isTakenFirst = false;
    await page.route(`**/conversations/${conversationId}/assign`, async (route) => {
      if (!isTakenFirst) {
        isTakenFirst = true;
        await assignByApi(request, owner.token, owner.businessId, conversationId, ownerId);
      }
      await route.continue();
    });
    await assignButton.click();
    const menu = page.getByRole("menu", { name: en.inbox.assign.menuLabel });
    await menu.getByRole("menuitemradio", { name: new RegExp(`^${en.inbox.assign.takeIt} \\(${en.inbox.assign.you}\\)`) }).click();

    await expect(page.getByText(en.inbox.assign.conflict)).toBeVisible();
    // How it stands now: the owner handles it, not the staff member.
    await expect(page.getByRole("button", { name: new RegExp(`^Handled by .+\\. ${en.inbox.assign.menuLabel}$`) })).toBeVisible();
    await expect(page.getByRole("button", { name: new RegExp(`^${en.inbox.assign.handledByYou}`) })).toHaveCount(0);
    expect((await cardOf(request, owner.token, owner.businessId, conversationId)).assignment?.assignee_user_id).toBe(ownerId);
  } finally {
    await staff.context.close();
  }
});

test("the team's notes never reach the customer's chat or the transcript", async ({ page, context, request }) => {
  const owner = await signInAsDemoOwner(request);
  await signInContext(context, owner.token);
  await page.setViewportSize(PHONE.viewport);
  const visitor = await visitorAsksForPerson(request, owner.businessId, `Inbox visitor ${uniqueSuffix()}`);
  const conversationId = await waitingConversationOf(request, owner.token, owner.businessId, visitor.name);
  await page.goto(`/b/${owner.businessId}/inbox/${conversationId}`);

  await page.getByRole("button", { name: en.inboxCard.openNotes, exact: true }).click();
  const panel = page.getByRole("dialog", { name: en.inboxCard.panelLabel });
  const note = `Promised a window table for Friday. ${uniqueSuffix()}`;
  await panel.getByRole("textbox", { name: en.inboxCard.notes.hint }).fill(note);
  await panel.getByRole("button", { name: en.inboxCard.notes.add, exact: true }).click();
  await expect(page.getByText(en.inboxCard.notes.added)).toBeVisible();
  await expect(panel.getByRole("list", { name: en.inboxCard.notes.title }).getByText(note)).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(panel).toBeHidden();

  // The note counts on the notes button, and nowhere in the conversation itself.
  const notesButton = page.getByRole("button", { name: en.inboxCard.openNotesCount.one.replace("{count}", "1"), exact: true });
  await expect(notesButton).toBeVisible();
  const transcript = page.getByRole("region", { name: en.conversations.transcript });
  await expect(transcript).toBeVisible();
  await expect(transcript.getByText(note)).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole("region", { name: en.conversations.transcript })).toBeVisible();
  await expect(page.getByText(note)).toHaveCount(0);
  expect((await cardOf(request, owner.token, owner.businessId, conversationId)).messages.map((message) => message.text)).not.toContain(note);
  expect(await visitorTranscript(request, owner.businessId, visitor)).not.toContain(note);
});
